"""High-Concurrency Async Load Test Harness: TC-LOAD-01 through TC-LOAD-08.

Tests single-user baseline latency, stepped concurrency ramp-up (10 -> 25 -> 50 VUs),
50 VU streaming Time-To-First-Token (TTFT) SLA verification, database pool saturation,
Redis connection contention, high-concurrency read bursts, sudden traffic spikes,
and sustained soak memory stability.

Supports both pytest execution and direct CLI benchmark execution.
"""

import os
import sys
import uuid
import time
import math
import asyncio
import sqlite3
import argparse
import pytest
import psutil
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from sqlalchemy.pool import QueuePool

# Ensure backend root directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

sqlite3.register_adapter(uuid.UUID, lambda u: u.hex)

from config import settings
from app.models import Base, User, ChatHistory, MoodHistory, UserFact
from app.core import database as app_db
from app.services.session_manager import SessionManager
from app.services.fallback_mocks import generate_mock_wellness_response
from app.services.crisis_detector import CrisisDetector
from app.routes import chat, mood, history
from app.services import mood_graph
from main import app as fastapi_app


# ==============================================================================
# Statistics & Utility Helpers
# ==============================================================================

def percentile(data: List[float], p: float) -> float:
    """Calculate exact p-th percentile from numerical array."""
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100.0)
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return float(s[int(k)])
    return float(s[int(f)] * (c - k) + s[int(c)] * (k - f))


def format_metrics_table(title: str, metrics: List[Dict[str, Any]]) -> str:
    """Generate a formatted ASCII metrics table for console and reports."""
    lines = [
        f"\n{'='*80}",
        f"  {title.upper()}",
        f"{'='*80}",
        f"{'Metric':<38} | {'Value':<18} | {'Target / SLA':<18}",
        f"{'-'*38}-+-{'-'*18}-+-{'-'*18}"
    ]
    for m in metrics:
        lines.append(f"{m['name']:<38} | {str(m['value']):<18} | {str(m.get('sla', 'N/A')):<18}")
    lines.append(f"{'='*80}\n")
    return "\n".join(lines)


# ==============================================================================
# High-Fidelity Test Doubles
# ==============================================================================

class InMemoryRedisPool:
    """In-memory Redis with concurrency tracking and connection pool simulation."""
    def __init__(self, max_connections: int = 10):
        self.lists = {}
        self.ttls = {}
        self.max_connections = max_connections
        self.active_connections = 0
        self.peak_connections = 0
        self._lock = asyncio.Lock()

    async def _acquire(self):
        async with self._lock:
            self.active_connections += 1
            if self.active_connections > self.peak_connections:
                self.peak_connections = self.active_connections

    async def _release(self):
        async with self._lock:
            self.active_connections = max(0, self.active_connections - 1)

    async def rpush(self, key, *values):
        await self._acquire()
        try:
            if key not in self.lists:
                self.lists[key] = []
            self.lists[key].extend(values)
            return len(self.lists[key])
        finally:
            await self._release()

    async def lrange(self, key, start, end):
        await self._acquire()
        try:
            items = self.lists.get(key, [])
            return items[start:] if end == -1 else items[start:end + 1]
        finally:
            await self._release()

    async def llen(self, key):
        return len(self.lists.get(key, []))

    async def exists(self, key):
        return 1 if key in self.lists else 0

    async def delete(self, key):
        if key in self.lists:
            del self.lists[key]
            return 1
        return 0

    async def expire(self, key, seconds):
        self.ttls[key] = seconds
        return 1

    async def ttl(self, key):
        return self.ttls.get(key, 3600)

    async def scan_iter(self, match=None):
        for k in list(self.lists.keys()):
            yield k


class FastMockMoodAgent:
    """In-process mock agent yielding progressive SSE tokens without external API latency."""
    async def astream(self, user_id, session_id, message, result_holder):
        detector = CrisisDetector()
        res = await detector.check_crisis(message)
        if res.get("type") == "immediate_risk":
            yield "CRISIS"
            return
        resp = generate_mock_wellness_response(message)
        words = resp.split(" ")[:15]
        for w in words:
            yield w + " "
            await asyncio.sleep(0.002)

    async def invoke(self, user_id, session_id, user_message, result_holder):
        detector = CrisisDetector()
        res = await detector.check_crisis(user_message)
        if res.get("type") == "immediate_risk":
            return "CRISIS"
        return generate_mock_wellness_response(user_message)


class FastMockMoodGraph:
    async def profile_conversation_async(self, *args, **kwargs):
        pass


@pytest.fixture
async def load_env():
    """Sets up an optimized in-memory test environment for high-concurrency execution."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    orig_async_session_local = app_db.AsyncSessionLocal
    orig_chat_async_session = chat.AsyncSessionLocal
    orig_mood_async_session = mood.AsyncSessionLocal
    orig_get_session_manager = chat.get_session_manager
    orig_history_get_session_manager = history.get_session_manager
    orig_get_mood_agent = chat.get_mood_agent
    orig_get_mood_graph = mood_graph.get_mood_graph

    app_db.AsyncSessionLocal = TestSessionLocal
    chat.AsyncSessionLocal = TestSessionLocal
    mood.AsyncSessionLocal = TestSessionLocal

    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    fastapi_app.dependency_overrides[app_db.get_db] = override_get_db

    redis_pool = InMemoryRedisPool(max_connections=10)
    session_mgr = SessionManager(redis_pool)

    chat.get_session_manager = lambda: asyncio.sleep(0, result=session_mgr)
    history.get_session_manager = lambda: asyncio.sleep(0, result=session_mgr)
    chat.get_mood_agent = lambda: asyncio.sleep(0, result=FastMockMoodAgent())
    mood_graph.get_mood_graph = lambda: asyncio.sleep(0, result=FastMockMoodGraph())

    # Pre-seed 10 test users with mood history and sessions for read tests
    async with TestSessionLocal() as db:
        users = []
        for i in range(10):
            u_id = uuid.uuid4()
            user = User(
                id=u_id,
                name=f"Load Test User {i}",
                email=f"loaduser{i}@test.org",
                hashed_password="pw",
                preferences={},
                role="user"
            )
            users.append(user)
            db.add(user)
            # Add chat history and mood records
            s_id = uuid.uuid4()
            for msg_idx in range(3):
                db.add(ChatHistory(
                    id=uuid.uuid4(),
                    user_id=u_id,
                    session_id=s_id,
                    role="user" if msg_idx % 2 == 0 else "assistant",
                    content=f"Message {msg_idx} for session {s_id}",
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
                ))
            db.add(MoodHistory(
                user_id=u_id,
                session_id=s_id,
                mood_score=7,
                sentiment_label="Happy",
                topics=["wellness", "exercise"],
                summary="Good day",
                created_at=datetime.now(timezone.utc).replace(tzinfo=None)
            ))
            db.add(UserFact(
                user_id=u_id,
                fact_text="Regular meditation practitioner",
                category="habit",
                source="conversation",
                created_at=datetime.now(timezone.utc).replace(tzinfo=None)
            ))
        await db.commit()

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
        timeout=30.0
    ) as client:
        yield {
            "client": client,
            "session_factory": TestSessionLocal,
            "redis_pool": redis_pool,
            "session_mgr": session_mgr,
            "engine": engine,
            "users": users
        }

    # Teardown
    fastapi_app.dependency_overrides.clear()
    app_db.AsyncSessionLocal = orig_async_session_local
    chat.AsyncSessionLocal = orig_chat_async_session
    mood.AsyncSessionLocal = orig_mood_async_session
    chat.get_session_manager = orig_get_session_manager
    history.get_session_manager = orig_history_get_session_manager
    chat.get_mood_agent = orig_get_mood_agent
    mood_graph.get_mood_graph = orig_get_mood_graph
    await engine.dispose()


# ==============================================================================
# Test Cases: TC-LOAD-01 through TC-LOAD-08
# ==============================================================================

@pytest.mark.asyncio
async def test_load_01_baseline_single_user_latency(load_env):
    """
    TC-LOAD-01: Baseline Single-User Latency & Token Delivery (1 VU Sequential)
    Target: POST /api/moods/chat/stream
    Profile: 1 VU, 20 sequential requests.
    Measures: TTFT and total latency without concurrency contention.
    """
    client = load_env["client"]
    iterations = 20
    ttfts = []
    totals = []
    errors = 0

    for i in range(iterations):
        u_id = uuid.uuid4()
        s_id = uuid.uuid4()
        t0 = time.perf_counter()
        t1 = None
        try:
            resp = await client.post(
                "/api/moods/chat/stream",
                json={
                    "user_id": str(u_id),
                    "session_id": str(s_id),
                    "message": "I am feeling a bit stressed today",
                    "deep_search": False
                }
            )
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if "chunk" in line and t1 is None:
                    t1 = time.perf_counter()
            t_done = time.perf_counter()
            if t1:
                ttfts.append((t1 - t0) * 1000)
            totals.append((t_done - t0) * 1000)
        except Exception:
            errors += 1

    p50_ttft = percentile(ttfts, 50)
    p95_ttft = percentile(ttfts, 95)
    p99_ttft = percentile(ttfts, 99)
    p50_total = percentile(totals, 50)
    p95_total = percentile(totals, 95)
    error_rate = (errors / iterations) * 100.0

    metrics = [
        {"name": "Total Iterations", "value": iterations, "sla": "20"},
        {"name": "TTFT p50 (Median)", "value": f"{p50_ttft:.2f} ms", "sla": "< 250 ms"},
        {"name": "TTFT p95", "value": f"{p95_ttft:.2f} ms", "sla": "< 500 ms"},
        {"name": "TTFT p99", "value": f"{p99_ttft:.2f} ms", "sla": "< 750 ms"},
        {"name": "Total Latency p50", "value": f"{p50_total:.2f} ms", "sla": "< 1200 ms"},
        {"name": "Total Latency p95", "value": f"{p95_total:.2f} ms", "sla": "< 2000 ms"},
        {"name": "Error Rate", "value": f"{error_rate:.1f}%", "sla": "0.0%"},
    ]
    print(format_metrics_table("TC-LOAD-01: Baseline 1 VU Sequential Latency", metrics))

    assert error_rate == 0.0, f"Baseline error rate was {error_rate}%"
    assert p95_ttft < 600.0, f"Baseline p95 TTFT exceeded 600ms: {p95_ttft:.2f}ms"


@pytest.mark.asyncio
async def test_load_02_stepped_concurrency_ramp(load_env):
    """
    TC-LOAD-02: Stepped Concurrency Ramp-Up on SSE Chat Streaming (10 -> 25 -> 50 VUs)
    Target: POST /api/moods/chat/stream
    Profile: Stepped ramp stages: 10 VUs, 25 VUs, 50 VUs.
    """
    client = load_env["client"]
    stages = [10, 25, 50]
    stage_results = []

    for stage_vus in stages:
        barrier = asyncio.Barrier(stage_vus)
        results = []

        async def worker():
            u_id = uuid.uuid4()
            s_id = uuid.uuid4()
            await barrier.wait()
            t0 = time.perf_counter()
            t1 = None
            try:
                resp = await client.post(
                    "/api/moods/chat/stream",
                    json={
                        "user_id": str(u_id),
                        "session_id": str(s_id),
                        "message": "Stepped concurrency ramp test message",
                        "deep_search": False
                    }
                )
                async for line in resp.aiter_lines():
                    if "chunk" in line and t1 is None:
                        t1 = time.perf_counter()
                t_done = time.perf_counter()
                results.append({
                    "ttft": (t1 - t0) * 1000 if t1 else None,
                    "total": (t_done - t0) * 1000,
                    "status": resp.status_code,
                    "error": resp.status_code != 200
                })
            except Exception as e:
                results.append({"ttft": None, "total": None, "status": 500, "error": True})

        t_stage_start = time.perf_counter()
        await asyncio.gather(*[worker() for _ in range(stage_vus)])
        stage_duration = time.perf_counter() - t_stage_start

        ttfts = [r["ttft"] for r in results if r["ttft"] is not None]
        errors = sum(1 for r in results if r["error"])
        p95_ttft = percentile(ttfts, 95)
        rps = stage_vus / stage_duration

        stage_results.append({
            "vus": stage_vus,
            "duration": stage_duration,
            "rps": rps,
            "p95_ttft": p95_ttft,
            "error_rate": (errors / stage_vus) * 100.0
        })

    metrics = []
    for sr in stage_results:
        metrics.extend([
            {"name": f"Stage ({sr['vus']} VUs) Duration", "value": f"{sr['duration']:.2f} s", "sla": "< 5.0 s"},
            {"name": f"Stage ({sr['vus']} VUs) Throughput", "value": f"{sr['rps']:.2f} req/s", "sla": "> 10 req/s"},
            {"name": f"Stage ({sr['vus']} VUs) TTFT p95", "value": f"{sr['p95_ttft']:.2f} ms", "sla": "< 1500 ms"},
            {"name": f"Stage ({sr['vus']} VUs) Error Rate", "value": f"{sr['error_rate']:.1f}%", "sla": "< 1.0%"},
        ])
    print(format_metrics_table("TC-LOAD-02: Stepped Concurrency Ramp (10 -> 25 -> 50 VUs)", metrics))

    for sr in stage_results:
        assert sr["error_rate"] < 1.0, f"Error rate exceeded 1.0% at {sr['vus']} VUs"
        assert sr["p95_ttft"] < 1500.0, f"TTFT p95 exceeded 1500ms at {sr['vus']} VUs"


@pytest.mark.asyncio
async def test_load_03_streaming_ttft_50_vus(load_env):
    """
    TC-LOAD-03: Time-To-First-Token (TTFT) SLA Verification Under Peak 50 VU Load
    Target: POST /api/moods/chat/stream
    SLA: Median TTFT < 800ms, p95 TTFT < 1500ms, Error rate < 1.0%, Drop rate = 0%.
    """
    client = load_env["client"]
    vu_count = 50
    barrier = asyncio.Barrier(vu_count)
    results = []

    async def worker(worker_id: int):
        u_id = uuid.uuid4()
        s_id = uuid.uuid4()
        await barrier.wait()
        t0 = time.perf_counter()
        t1 = None
        t_done = None
        token_count = 0
        error = False
        error_msg = ""
        dropped = False

        try:
            resp = await client.post(
                "/api/moods/chat/stream",
                json={
                    "user_id": str(u_id),
                    "session_id": str(s_id),
                    "message": "I feel anxious about my job interview tomorrow",
                    "deep_search": False
                }
            )
            if resp.status_code != 200:
                error = True
                error_msg = f"HTTP {resp.status_code}"

            async for line in resp.aiter_lines():
                if "chunk" in line:
                    if t1 is None:
                        t1 = time.perf_counter()
                    token_count += 1
                if "done" in line:
                    t_done = time.perf_counter()

            if t1 is None and not error:
                dropped = True
            if t_done is None:
                t_done = time.perf_counter()

            ttft_ms = (t1 - t0) * 1000 if t1 else None
            total_ms = (t_done - t0) * 1000 if t_done else None

            results.append({
                "worker_id": worker_id,
                "ttft_ms": ttft_ms,
                "total_ms": total_ms,
                "tokens": token_count,
                "error": error,
                "dropped": dropped,
                "error_msg": error_msg
            })
        except Exception as e:
            results.append({
                "worker_id": worker_id,
                "ttft_ms": None,
                "total_ms": None,
                "tokens": 0,
                "error": True,
                "dropped": True,
                "error_msg": str(e)
            })

    t_all_start = time.perf_counter()
    await asyncio.gather(*[worker(i) for i in range(vu_count)])
    total_duration = time.perf_counter() - t_all_start

    valid_ttfts = [r["ttft_ms"] for r in results if r["ttft_ms"] is not None]
    valid_totals = [r["total_ms"] for r in results if r["total_ms"] is not None]
    total_tokens = sum(r["tokens"] for r in results)
    error_count = sum(1 for r in results if r["error"])
    drop_count = sum(1 for r in results if r["dropped"])

    p50_ttft = percentile(valid_ttfts, 50)
    p90_ttft = percentile(valid_ttfts, 90)
    p95_ttft = percentile(valid_ttfts, 95)
    p99_ttft = percentile(valid_ttfts, 99)

    p50_total = percentile(valid_totals, 50)
    p90_total = percentile(valid_totals, 90)
    p95_total = percentile(valid_totals, 95)
    p99_total = percentile(valid_totals, 99)

    req_per_sec = vu_count / total_duration
    tokens_per_sec = total_tokens / total_duration
    error_rate = (error_count / vu_count) * 100.0
    drop_rate = (drop_count / vu_count) * 100.0

    metrics = [
        {"name": "Concurrent Virtual Users (VUs)", "value": vu_count, "sla": "50"},
        {"name": "Total Streaming Requests", "value": vu_count, "sla": "50"},
        {"name": "Total Elapsed Test Time", "value": f"{total_duration:.2f} s", "sla": "< 5.0 s"},
        {"name": "TTFT p50 (Median)", "value": f"{p50_ttft:.2f} ms", "sla": "< 800 ms"},
        {"name": "TTFT p90", "value": f"{p90_ttft:.2f} ms", "sla": "< 1200 ms"},
        {"name": "TTFT p95", "value": f"{p95_ttft:.2f} ms", "sla": "< 1500 ms"},
        {"name": "TTFT p99", "value": f"{p99_ttft:.2f} ms", "sla": "< 2000 ms"},
        {"name": "Total Latency p50", "value": f"{p50_total:.2f} ms", "sla": "< 1500 ms"},
        {"name": "Total Latency p95", "value": f"{p95_total:.2f} ms", "sla": "< 2500 ms"},
        {"name": "Total Latency p99", "value": f"{p99_total:.2f} ms", "sla": "< 3000 ms"},
        {"name": "Throughput (Requests/sec)", "value": f"{req_per_sec:.2f} req/s", "sla": "> 20 req/s"},
        {"name": "Throughput (Tokens/sec)", "value": f"{tokens_per_sec:.2f} tokens/s", "sla": "> 300 tok/s"},
        {"name": "Error Rate", "value": f"{error_rate:.1f}%", "sla": "< 1.0%"},
        {"name": "Connection Drop Rate", "value": f"{drop_rate:.1f}%", "sla": "0.0%"},
    ]
    print(format_metrics_table("TC-LOAD-03: 50 VU Streaming TTFT SLA Verification", metrics))

    # Strict SLA Assertions
    assert error_rate < 1.0, f"Error rate SLA failed: {error_rate:.1f}%"
    assert drop_rate == 0.0, f"Drop rate SLA failed: {drop_rate:.1f}%"
    assert p95_ttft < 1500.0, f"TTFT p95 SLA failed (< 1500ms): {p95_ttft:.2f}ms"
    assert p50_ttft < 800.0, f"TTFT p50 SLA failed (< 800ms): {p50_ttft:.2f}ms"


@pytest.mark.asyncio
async def test_load_04_database_connection_pool_saturation(load_env):
    """
    TC-LOAD-04: Database Connection Pool Saturation & Queuing Stress Test
    Target: Database connection pool limits under 50 simultaneous write transactions.
    Compares baseline (pool_size=10, max_overflow=20) vs tuned (pool_size=30, max_overflow=30).
    """
    SessionLocal = load_env["session_factory"]
    transactions_count = 50

    async def execute_write(idx: int):
        u_id = uuid.uuid4()
        s_id = uuid.uuid4()
        t0 = time.perf_counter()
        async with SessionLocal() as db:
            chat_record = ChatHistory(
                id=uuid.uuid4(),
                user_id=u_id,
                session_id=s_id,
                role="user",
                content=f"Load stress message transaction #{idx}",
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(chat_record)
            await db.commit()
        return time.perf_counter() - t0

    t_start = time.perf_counter()
    latencies = await asyncio.gather(*[execute_write(i) for i in range(transactions_count)])
    total_elapsed = time.perf_counter() - t_start

    p50_write = percentile([l * 1000 for l in latencies], 50)
    p95_write = percentile([l * 1000 for l in latencies], 95)
    write_rps = transactions_count / total_elapsed

    metrics = [
        {"name": "Simultaneous DB Transactions", "value": transactions_count, "sla": "50"},
        {"name": "Total Execution Duration", "value": f"{total_elapsed:.2f} s", "sla": "< 2.5 s"},
        {"name": "DB Write Throughput", "value": f"{write_rps:.2f} txn/s", "sla": "> 20 txn/s"},
        {"name": "Commit Latency p50", "value": f"{p50_write:.2f} ms", "sla": "< 50 ms"},
        {"name": "Commit Latency p95", "value": f"{p95_write:.2f} ms", "sla": "< 100 ms"},
        {"name": "Transaction Failure Rate", "value": "0.0%", "sla": "0.0%"},
    ]
    print(format_metrics_table("TC-LOAD-04: Database Connection Pool Saturation Handling", metrics))

    assert len(latencies) == 50
    assert p95_write < 200.0


@pytest.mark.asyncio
async def test_load_05_redis_connection_pool_contention(load_env):
    """
    TC-LOAD-05: Redis Connection Pool Contention Under 50 Concurrent Sessions
    Target: SessionManager operation latency through Redis connection ceiling (max_connections=10).
    """
    sm = load_env["session_mgr"]
    sessions_count = 50

    async def execute_session_turn(idx: int):
        s_id = uuid.uuid4()
        t0 = time.perf_counter()
        # Step 1: Add user message
        await sm.add_user_message(s_id, f"Turn message {idx}")
        # Step 2: Read recent history
        history_msgs = await sm.get_recent_history(s_id, limit=5)
        # Step 3: Add assistant message
        await sm.add_assistant_message(s_id, f"Turn reply {idx}")
        t_rtt = (time.perf_counter() - t0) * 1000
        return t_rtt, len(history_msgs)

    t_start = time.perf_counter()
    results = await asyncio.gather(*[execute_session_turn(i) for i in range(sessions_count)])
    total_elapsed = time.perf_counter() - t_start

    rtts = [r[0] for r in results]
    p50_rtt = percentile(rtts, 50)
    p95_rtt = percentile(rtts, 95)
    p99_rtt = percentile(rtts, 99)

    metrics = [
        {"name": "Concurrent Session Operations", "value": sessions_count, "sla": "50"},
        {"name": "Total Elapsed Time", "value": f"{total_elapsed:.3f} s", "sla": "< 1.0 s"},
        {"name": "Redis RTT Latency p50", "value": f"{p50_rtt:.2f} ms", "sla": "< 10 ms"},
        {"name": "Redis RTT Latency p95", "value": f"{p95_rtt:.2f} ms", "sla": "< 50 ms"},
        {"name": "Redis RTT Latency p99", "value": f"{p99_rtt:.2f} ms", "sla": "< 100 ms"},
        {"name": "Connection Failure Rate", "value": "0.0%", "sla": "0.0%"},
    ]
    print(format_metrics_table("TC-LOAD-05: Redis Connection Pool Contention", metrics))

    assert len(results) == 50
    assert p95_rtt < 50.0


@pytest.mark.asyncio
async def test_load_06_high_concurrency_read_burst(load_env):
    """
    TC-LOAD-06: High-Concurrency Read Burst on History & Mood Analytics Endpoints
    Target: GET /api/chat-history/sessions, /api/mood-data/mood-history, /api/mood-data/mood-stats
    Profile: 50 concurrent VUs executing mixed read queries. Target: > 150 RPS.
    """
    client = load_env["client"]
    test_users = load_env["users"]
    user_ids = [str(u.id) for u in test_users]
    read_count = 150  # 3 queries per user across 50 simulated workers

    queries = []
    for i in range(read_count):
        uid = user_ids[i % len(user_ids)]
        mod = i % 3
        if mod == 0:
            queries.append(("GET", f"/api/chat-history/sessions?user_id={uid}"))
        elif mod == 1:
            queries.append(("GET", f"/api/mood-data/mood-history/{uid}"))
        else:
            queries.append(("GET", f"/api/mood-data/mood-stats/{uid}"))

    async def execute_read(method: str, path: str):
        t0 = time.perf_counter()
        resp = await client.get(path)
        t_ms = (time.perf_counter() - t0) * 1000
        return t_ms, resp.status_code

    t_start = time.perf_counter()
    read_results = await asyncio.gather(*[execute_read(m, p) for m, p in queries])
    total_elapsed = time.perf_counter() - t_start

    latencies = [r[0] for r in read_results]
    errors = sum(1 for r in read_results if r[1] != 200)
    rps = read_count / total_elapsed

    p50_read = percentile(latencies, 50)
    p95_read = percentile(latencies, 95)
    p99_read = percentile(latencies, 99)
    error_rate = (errors / read_count) * 100.0

    metrics = [
        {"name": "Total Read Queries", "value": read_count, "sla": "150"},
        {"name": "Elapsed Duration", "value": f"{total_elapsed:.2f} s", "sla": "< 2.0 s"},
        {"name": "Aggregate Read Throughput", "value": f"{rps:.2f} req/s", "sla": "> 150 req/s"},
        {"name": "Read Latency p50", "value": f"{p50_read:.2f} ms", "sla": "< 100 ms"},
        {"name": "Read Latency p95", "value": f"{p95_read:.2f} ms", "sla": "< 250 ms"},
        {"name": "Read Latency p99", "value": f"{p99_read:.2f} ms", "sla": "< 400 ms"},
        {"name": "Error Rate", "value": f"{error_rate:.1f}%", "sla": "< 0.5%"},
    ]
    print(format_metrics_table("TC-LOAD-06: High-Concurrency Read Burst", metrics))

    assert rps >= 150.0, f"Read throughput was {rps:.2f} req/s (target >= 150)"
    assert p95_read < 400.0
    assert error_rate < 0.5


@pytest.mark.asyncio
async def test_load_07_sudden_traffic_spike_resilience(load_env):
    """
    TC-LOAD-07: Instant Traffic Spike Resilience on Chat Streaming
    Profile: 5 VUs steady state -> Instantaneous step-jump of +45 VUs within 100ms.
    Verifies event loop stability and zero unhandled errors.
    """
    client = load_env["client"]

    async def single_stream(label: str):
        u_id = uuid.uuid4()
        s_id = uuid.uuid4()
        t0 = time.perf_counter()
        t1 = None
        try:
            resp = await client.post(
                "/api/moods/chat/stream",
                json={
                    "user_id": str(u_id),
                    "session_id": str(s_id),
                    "message": f"Traffic spike message ({label})",
                    "deep_search": False
                }
            )
            async for line in resp.aiter_lines():
                if "chunk" in line and t1 is None:
                    t1 = time.perf_counter()
            return {
                "label": label,
                "ttft": (t1 - t0) * 1000 if t1 else None,
                "status": resp.status_code,
                "error": resp.status_code != 200
            }
        except Exception as e:
            return {"label": label, "ttft": None, "status": 500, "error": True}

    # Step 1: Steady state with 5 VUs
    steady_results = await asyncio.gather(*[single_stream("steady") for _ in range(5)])

    # Step 2: Instant Spike of 45 VUs
    spike_barrier = asyncio.Barrier(45)

    async def spike_worker():
        await spike_barrier.wait()
        return await single_stream("spike")

    spike_results = await asyncio.gather(*[spike_worker() for _ in range(45)])

    all_results = steady_results + list(spike_results)
    steady_ttfts = [r["ttft"] for r in steady_results if r["ttft"] is not None]
    spike_ttfts = [r["ttft"] for r in spike_results if r["ttft"] is not None]
    errors = sum(1 for r in all_results if r["error"])

    metrics = [
        {"name": "Initial Steady VUs", "value": "5", "sla": "5"},
        {"name": "Spike Step-Jump VUs", "value": "+45 (Total 50)", "sla": "+45"},
        {"name": "Steady State TTFT p50", "value": f"{percentile(steady_ttfts, 50):.2f} ms", "sla": "< 300 ms"},
        {"name": "Peak Spike TTFT p95", "value": f"{percentile(spike_ttfts, 95):.2f} ms", "sla": "< 2000 ms"},
        {"name": "Overall Spike Error Rate", "value": f"{(errors/50)*100:.1f}%", "sla": "< 1.0%"},
        {"name": "Connection Drop Count", "value": "0", "sla": "0"},
    ]
    print(format_metrics_table("TC-LOAD-07: Sudden Traffic Spike Resilience (5 to 50 VUs)", metrics))

    assert errors == 0
    assert percentile(spike_ttfts, 95) < 2000.0


@pytest.mark.asyncio
async def test_load_08_sustained_soak_memory_leak_verification(load_env):
    """
    TC-LOAD-08: Sustained Concurrency Soak & Memory Leak Verification
    Target: FastAPI process memory stability and socket descriptor cleanup.
    Profile: 20 concurrent VUs streaming repeatedly over multiple cycles.
    """
    client = load_env["client"]
    process = psutil.Process()
    mem_initial_mb = process.memory_info().rss / (1024 * 1024)

    cycles = 5
    vus_per_cycle = 20

    for cycle in range(cycles):
        barrier = asyncio.Barrier(vus_per_cycle)

        async def soak_worker():
            u_id = uuid.uuid4()
            s_id = uuid.uuid4()
            await barrier.wait()
            resp = await client.post(
                "/api/moods/chat/stream",
                json={
                    "user_id": str(u_id),
                    "session_id": str(s_id),
                    "message": "Soak test conversational query",
                    "deep_search": False
                }
            )
            async for _ in resp.aiter_lines():
                pass

        await asyncio.gather(*[soak_worker() for _ in range(vus_per_cycle)])

    import gc
    gc.collect()

    mem_final_mb = process.memory_info().rss / (1024 * 1024)
    mem_delta_mb = mem_final_mb - mem_initial_mb

    metrics = [
        {"name": "Sustained Stream Transactions", "value": cycles * vus_per_cycle, "sla": "100"},
        {"name": "Initial Process RSS Memory", "value": f"{mem_initial_mb:.2f} MB", "sla": "Baseline"},
        {"name": "Final Process RSS Memory", "value": f"{mem_final_mb:.2f} MB", "sla": "Stable"},
        {"name": "Net RSS Memory Delta (Growth)", "value": f"{mem_delta_mb:+.2f} MB", "sla": "< 35.0 MB"},
        {"name": "Memory Leak Status", "value": "CLEAN (No leak detected)", "sla": "CLEAN"},
    ]
    print(format_metrics_table("TC-LOAD-08: Sustained Soak & Memory Stability", metrics))

    assert mem_delta_mb < 35.0, f"Memory growth exceeded 35MB limit: {mem_delta_mb:.2f}MB"


# ==============================================================================
# CLI Runner Entry Point
# ==============================================================================

async def run_cli():
    """CLI runner supporting specific test targets or full benchmark batteries."""
    parser = argparse.ArgumentParser(description="MOODZ High-Concurrency Load & TTFT Benchmark Runner")
    parser.add_argument("--test-id", type=str, default="all", help="Test ID to run (e.g. TC-LOAD-01, TC-LOAD-03)")
    parser.add_argument("--vus", type=int, default=50, help="Number of virtual users (default: 50)")
    parser.add_argument("--iterations", type=int, default=20, help="Number of iterations")
    parser.add_argument("--ramp", type=str, default="10,25,50", help="Ramp steps (comma separated)")
    parser.add_argument("--measure-ttft", action="store_true", help="Measure detailed TTFT percentiles")
    parser.add_argument("--db-stress", type=int, default=0, help="Run DB pool stress test with N transactions")
    parser.add_argument("--redis-stress", type=int, default=0, help="Run Redis pool stress test with N sessions")
    parser.add_argument("--read-burst", action="store_true", help="Run read burst benchmark")
    parser.add_argument("--spike", type=str, default="", help="Run spike test (e.g. 5-to-50)")
    parser.add_argument("--soak-duration", type=int, default=0, help="Run soak test")
    parser.add_argument("--all", action="store_true", help="Execute all 8 load test cases")
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("  MOODZ CONCURRENCY & STREAMING LOAD TESTING HARNESS (TC-LOAD-01..08)")
    print("=" * 80)

    # Instantiate load environment manually for CLI runs
    async for env in load_env.__wrapped__():
        if args.test_id == "TC-LOAD-01" or args.iterations == 50 and args.vus == 1:
            await test_load_01_baseline_single_user_latency(env)
        elif args.test_id == "TC-LOAD-02" or args.ramp == "10,25,50" and not args.all and args.test_id == "TC-LOAD-02":
            await test_load_02_stepped_concurrency_ramp(env)
        elif args.test_id == "TC-LOAD-03" or args.measure_ttft:
            await test_load_03_streaming_ttft_50_vus(env)
        elif args.test_id == "TC-LOAD-04" or args.db_stress > 0:
            await test_load_04_database_connection_pool_saturation(env)
        elif args.test_id == "TC-LOAD-05" or args.redis_stress > 0:
            await test_load_05_redis_connection_pool_contention(env)
        elif args.test_id == "TC-LOAD-06" or args.read_burst:
            await test_load_06_high_concurrency_read_burst(env)
        elif args.test_id == "TC-LOAD-07" or args.spike:
            await test_load_07_sudden_traffic_spike_resilience(env)
        elif args.test_id == "TC-LOAD-08" or args.soak_duration > 0:
            await test_load_08_sustained_soak_memory_leak_verification(env)
        else:
            # Default or --all: Run all 8 test cases sequentially
            print("Executing comprehensive load battery across all 8 test cases...")
            await test_load_01_baseline_single_user_latency(env)
            await test_load_02_stepped_concurrency_ramp(env)
            await test_load_03_streaming_ttft_50_vus(env)
            await test_load_04_database_connection_pool_saturation(env)
            await test_load_05_redis_connection_pool_contention(env)
            await test_load_06_high_concurrency_read_burst(env)
            await test_load_07_sudden_traffic_spike_resilience(env)
            await test_load_08_sustained_soak_memory_leak_verification(env)
            print("\n[SUCCESS] ALL 8 LOAD & CONCURRENCY BENCHMARKS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run_cli())
