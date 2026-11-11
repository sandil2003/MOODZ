# Handoff Report: Security, Load Testing, Streaming Latency & CI/CD Audit

**Agent**: Explorer 3 (Security, Load Testing & Preliminary Test Plan Reference Explorer)  
**Date**: 2026-10-31  
**Working Directory**: `c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\explorer_survey_3\`  
**Target Reference Plan**: `C:\Users\sandi\.gemini\antigravity\brain\b1b115c5-4e5e-4005-bef2-4ddea0005453\comprehensive_test_plan.md`  
**Target Report Destination**: `docs/comprehensive_test_plan.md` & `docs/comprehensive_test_results_report.md`  

---

## 1. Observation

### 1.1 Preliminary Test Plan Analysis (`comprehensive_test_plan.md`)
Direct review of `C:\Users\sandi\.gemini\antigravity\brain\b1b115c5-4e5e-4005-bef2-4ddea0005453\comprehensive_test_plan.md` indicates the following contents:
- **Disciplines Defined (Part 1, lines 72–86)**: 8 test disciplines: Unit Testing, Integration Testing, UI/Frontend Testing, Security & Privacy Testing, AI Safety & Crisis Gate, Performance & Load Testing, AgentOps & Behavioral Evals, and CI/CD Regression.
- **Formulated Test Matrices (Part 2, lines 89–150)**:
  - **2.1 UI & Frontend Matrix**: 10 concrete test cases (**TC-UI-01** to **TC-UI-10**) covering `auth.guard.ts`, auth forms, `new-home`, `mood-agent` signals, SSE stream ingestion, crisis alert banner (988 lifeline), `ngx-markdown`, dark mode persistence, `mood-history`, and `mood-dashboard`.
  - **2.2 Security & Vulnerability Matrix**: 12 test cases (**TC-SEC-01** to **TC-SEC-12**) covering JWT signature tampering, expiration, cross-tenant BOLA/IDOR on sessions, BOLA/IDOR on mood history, PII log scrubbing, prompt injection, suicide jailbreaking bypass, XSS, SQLi, CORS policy, password hashing, and API rate limiting.
  - **2.3 Load & Performance Matrix**: 6 test cases (**TC-LOAD-01** to **TC-LOAD-06**) covering baseline latency (1 VU, 50 requests), SSE concurrency ramp (10–50 VUs measuring TTFT), Auth/History RPS concurrency (100 VUs), stress spike (5–100 VUs), DB connection pool saturation (60 concurrent writes), and Redis state concurrency (100 ops).
  - **2.4 AI Safety & Crisis Gate Matrix**: 5 test cases (**TC-SAFE-01** to **TC-SAFE-05**) validating direct suicidal intent, self-harm, colloquial crisis expressions, and benign false positive controls with latency < 10ms.
- **Pipeline Gap Analysis (Part 3, lines 152–192)**:
  - Highlights failure of `npm test -- --run` in GitHub Actions.
  - Highlights broken spec file `new-home.spec.ts`.
  - Identifies lack of AST / SAST scanning, missing BOLA regression suite, missing automated load gate, and lack of migration verifications.
- **Items Requiring Update in the Final Plan (`docs/comprehensive_test_plan.md`)**:
  - The preliminary plan references non-existent test files (`backend/test/test_security_matrix.py` and `backend/test/test_load_concurrency.py`). Concrete scripts must be codified.
  - Connection pool configuration bottlenecks in `database.py` (`pool_size=10, max_overflow=20`) and `redis_client.py` (`max_connections=10`) must be explicitly addressed for TC-LOAD-02 and TC-LOAD-05.
  - The precise command syntax for Angular 21 unit testing (`--watch=false`) must replace `--run`.
  - Streaming TTFT handling: TTFT measurement must be clarified as an external client-side metric because the backend does not transmit TTFT in the SSE payload.

---

### 1.2 Backend Authentication & Authorization Boundaries (BOLA / IDOR Audit)

#### A. Token Extraction Dependency Available but Unused
In `backend/app/core/auth_utils.py` (lines 77–92):
```python
async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    return payload["sub"]
```
**Observation**: Ripgrep across the entire codebase reveals `get_current_user_id` is **never imported or referenced in any API router** (`chat.py`, `history.py`, `mood.py`, `health.py`, `auth.py`).

#### B. Broken Object Level Authorization (BOLA / IDOR) in `backend/app/routes/history.py`
1. **Unauthenticated Session Listing** (lines 36–41):
   ```python
   @chat_history_router.get("/sessions", response_model=List[ChatSessionSummary])
   async def get_chat_sessions(
       user_id: UUID = Query(..., description="User ID to fetch sessions for"),
       limit: int = Query(50, ge=1, le=100, description="Max sessions to return"),
       db: AsyncSession = Depends(get_db)
   ):
   ```
   *Behavior*: No authentication required. Any caller supplying an arbitrary `user_id` receives full session summaries, timestamps, and the verbatim `first_message` content of another user's therapy sessions.
2. **Unauthenticated Session Transcripts** (lines 88–93):
   ```python
   @chat_history_router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
   async def get_chat_session(
       session_id: UUID,
       user_id: UUID = Query(..., description="User ID for authorization"),
       db: AsyncSession = Depends(get_db)
   ):
   ```
   *Behavior*: Uses query parameter `user_id` for authorization instead of the caller's JWT `sub`. Anyone who supplies a target `user_id` and `session_id` can read complete therapy transcripts.
3. **Unauthenticated Redis Session Access & Deletion** (lines 143–207):
   - `GET /api/history/session/{session_id}` (line 143): Requires no authentication or user ownership check; returns raw Redis conversation history.
   - `GET /api/history/sessions/active` (line 174): Lists all active session IDs in Redis with zero authentication.
   - `DELETE /api/history/session/{session_id}` (line 187): Allows any unauthenticated client to purge another user's active session.

#### C. Broken Object Level Authorization (BOLA / IDOR) in `backend/app/routes/mood.py`
1. **Mood History Exposure** (lines 27–32):
   ```python
   @router.get("/mood-history/{user_id}", response_model=List[MoodHistoryResponse])
   async def get_mood_history(
       user_id: UUID,
       limit: int = Query(default=50, le=200),
       days: Optional[int] = Query(default=None, description="Filter by last N days")
   ):
   ```
   *Behavior*: Zero authentication. Returns emotional scores, sentiment labels, conversation summaries, and topics for any `user_id`.
2. **User Facts Exposure** (lines 64–69):
   ```python
   @router.get("/user-facts/{user_id}", response_model=List[UserFactResponse])
   async def get_user_facts(
       user_id: UUID,
       category: Optional[str] = Query(default=None, description="Filter by category"),
       limit: int = Query(default=100, le=500)
   ):
   ```
   *Behavior*: Returns auto-extracted personal facts (medical details, pets, workplace) with zero authentication.
3. **Mood Statistics Exposure** (lines 97–101):
   ```python
   @router.get("/mood-stats/{user_id}")
   async def get_mood_stats(user_id: UUID, days: int = Query(default=30)):
   ```
   *Behavior*: Returns calculated emotional trends and average scores without authentication.

#### D. Chat Endpoints Identity Decoupling in `backend/app/routes/chat.py`
1. **Chat Streaming** (lines 286–290):
   ```python
   @router.post("/stream", response_class=StreamingResponse)
   async def chat_stream(
       request: ChatRequest,
       background_tasks: BackgroundTasks
   ):
   ```
   *Behavior*: Accepts `request.user_id` directly from payload. No JWT token is verified or matched against `sub`.
2. **Synchronous Chat** (lines 332–336):
   `@router.post("/", response_model=ChatResponse)` similarly trusts `request.user_id`.

#### E. Client-Side Hardcoded User ID & Missing Bearer Headers
In `moodz-frontend/src/app/services/mood_agent/chat.service.ts`:
- Line 61: `private readonly DEMO_USER_ID = 'c47209cb-b2f1-4c76-a7ae-19805f3926b4';`
- Line 64: `private userId: string = this.DEMO_USER_ID;`
- Line 224:
  ```typescript
  const response = await fetch(`${this.API_BASE_URL}${this.STREAM_ENDPOINT}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
  });
  ```
- Lines 340–348:
  ```typescript
  const response = await fetch(`${this.API_BASE_URL}/api/chat-history/sessions?user_id=${this.userId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
  });
  ```
In `moodz-frontend/src/app/services/mood_agent/mood-data.service.ts`:
- Lines 44–49, 62–67, 76–81: Calls `fetch()` directly without passing `Authorization: Bearer <token>`.
In `moodz-frontend/src/app/pages/mood-dashboard/mood-dashboard.ts` (line 111) & `mood-history.ts` (line 38):
- `const userId = this.chatService.getUserId();` passes the hardcoded `DEMO_USER_ID`.

---

### 1.3 Streaming Endpoints, TTFT & Latency Handling

#### A. Architecture & Event Format
- **Endpoint**: `POST /api/moods/chat/stream` returns `StreamingResponse(media_type="text/event-stream")`.
- **Headers**: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`.
- **SSE Chunk Protocol** (`chat.py` lines 228–248, 273–279):
  - Progressive tokens: `data: {"chunk": "<text>"}\n\n`
  - Stream completion: `data: {"done": true, "session_id": "...", "latency": <total_seconds>, "classification": {...}}\n\n`
  - Crisis trigger: `data: {"chunk": "<988 message>"}\n\n` followed by `data: {"done": true, "session_id": "...", "crisis_detected": true}\n\n`
  - Error: `data: {"error": "Error: <msg>"}\n\n`

#### B. Bottlenecks Impacting Time-To-First-Token (TTFT)
In `backend/app/routes/chat.py` lines 223–225:
```python
await session_manager.add_user_message(session_id, message)
await save_chat_message_to_db(user_id, session_id, "user", message)
```
**Observation**: Two blocking network I/O operations occur **before** the generator invokes the LLM stream (`chain.astream`):
1. Redis list push (`add_user_message`).
2. PostgreSQL transaction (`save_chat_message_to_db`) performing `PIIScrubber.scrub_text` and an `INSERT INTO chat_history` commit.
If the database connection pool is under contention, TTFT increases directly by the database acquisition and commit latency.

#### C. Backend TTFT Tracking vs. Client Visibility
In `backend/app/services/mood_graph.py` lines 626–628:
```python
if not ttft_recorded:
    stream_span.set_attribute("moodz.ttft_ms", (time.perf_counter() - stream_start) * 1000)
    ttft_recorded = True
```
- TTFT is measured inside `mood_graph.py` from `stream_start = time.perf_counter()` to the first LLM token.
- **Deficiencies**:
  1. The metric does not account for the preceding Redis and PostgreSQL write times in `chat.py`.
  2. If the LLM throws an exception and enters fallback mock mode (lines 661–667), `ttft_recorded` is skipped and `moodz.ttft_ms` is never recorded.
  3. The SSE `done` event only provides `latency: round(latency, 3)` (total elapsed time), and never includes TTFT in the payload.
  4. TTFT must therefore be measured externally by test runners and frontend clients from request initiation to first `data: {"chunk": ...}` event.

---

### 1.4 Load Testing Infrastructure & Concurrency Ceilings

#### A. Tooling State
- Ripgrep and directory search confirm **no load testing scripts** (`locust`, `k6`, or custom test scripts) exist in the repository.
- `pip list` in virtual environment `.\moodz` confirms:
  - Installed: `httpx` (0.28.1), `httpx-sse` (0.4.3), `aiohttp` (3.13.2), `pytest` (9.1.1), `pytest-asyncio` (1.4.1), `asyncpg` (0.31.0).
  - Not installed: `locust`, `k6`.
- **Capability Assessment**: `httpx` + `httpx-sse` + `asyncio.gather` provides all required capabilities to run 50 concurrent virtual users streaming chat sessions against FastAPI without external tools.

#### B. Concurrency Bottlenecks Identified for 50 Concurrent VUs
1. **Database Connection Pool Exhaustion**:
   In `backend/app/core/database.py` (lines 11–12):
   ```python
   pool_size=10,
   max_overflow=20,
   ```
   Maximum concurrent connections = 30. If 50 concurrent virtual users initiate chat requests simultaneously, all 50 execute `save_chat_message_to_db` concurrently before streaming starts, exceeding the pool ceiling (30) and causing `sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 20 reached`.
2. **Redis Connection Limit**:
   In `backend/app/core/redis_client.py` (line 22):
   ```python
   max_connections=10
   ```
   A ceiling of 10 connections creates a serialization queue for 50 concurrent callers pushing user messages to Redis.
3. **Absence of Rate Limiting**:
   No rate limiting middleware or route limiter exists on `/api/moods/chat/stream`, allowing a single IP or user to consume unlimited backend threads and LLM quotas.

---

### 1.5 CI/CD Pipeline Configuration & Verbatim Execution Blockers

#### A. Direct Execution Failure 1: Angular Test Runner Argument Mismatch
In `.github/workflows/ci.yml` (line 66):
```yaml
      - name: Run tests
        run: npm test -- --run
```
**Direct Execution Verification**:
Executing `cd moodz-frontend; npm test -- --run` in terminal yields:
```text
> moodz-frontend@0.0.0 test
> ng test --run

Error: Unknown argument: run
Command exited with code 1.
```
*Cause*: Angular 21's `@angular/build:unit-test` builder does not accept `--run`. The correct argument for non-watch execution is `--watch=false` (or `--no-watch`).

#### B. Direct Execution Failure 2: TypeScript Import Error in `new-home.spec.ts`
Executing `cd moodz-frontend; npx ng test --watch=false` in terminal yields:
```text
√ Building...
Application bundle generation failed. [4.354 seconds]

X [ERROR] TS2305: Module '"./new-home"' has no exported member 'NewHome'. [plugin angular-compiler]

    src/app/pages/new-home/new-home.spec.ts:3:9:
      3 │ import { NewHome } from './new-home';
        ╵          ~~~~~~~
```
*Cause*: `moodz-frontend/src/app/pages/new-home/new-home.ts` (line 36) exports `NewHomeComponent`, but `new-home.spec.ts` (lines 3, 6, 7, 11, 15) attempts to import and instantiate `NewHome`.

#### C. CI/CD Pipeline Security & Quality Gaps
In `.github/workflows/ci.yml`:
1. **Zero SAST / Security Scanning**: No `bandit -r backend/app`, no `pip-audit`, no `npm audit --audit-level=high`.
2. **Missing BOLA / IDOR Verification**: No step executes authorization boundary tests against user data routes.
3. **Missing Automated Load Gate**: No headless test asserts TTFT thresholds (< 800ms) or verifies stability under 25–50 concurrent streaming sessions.
4. **No Database Migration Validation**: No `alembic upgrade head --dry-run` to ensure migration integrity.
5. **Partial Backend Test Execution**: Line 36 only runs `test_split_routes.py` and `test_normalization_logic.py`, ignoring all other unit and integration tests.
6. **No Test Coverage Enforcement**: No `pytest-cov` reporting or failure threshold.

---

## 2. Logic Chain

1. **Premise**: In mental wellness applications, emotional logs, personal facts, and therapy transcripts constitute sensitive personal health data.
2. **Observation**: `history.py` (lines 36, 88, 143) and `mood.py` (lines 27, 64, 97) accept `user_id` as an untrusted client query or path parameter and perform database reads without extracting or validating a caller's JWT token.
3. **Inference**: Any authenticated or unauthenticated party who learns or enumerates another user's UUID can read their private therapy sessions, mood ratings, and personal facts. This is an OWASP API Top 10 API1:2023 (BOLA) vulnerability.
4. **Observation**: Frontend `chat.service.ts` hardcodes `DEMO_USER_ID = 'c47209cb-b2f1-4c76-a7ae-19805f3926b4'` and does not supply Bearer tokens on `fetch()`, even though `AuthService` stores valid JWT tokens in `localStorage`.
5. **Inference**: Even if the backend were secured today, legitimate frontend users would immediately be locked out or continue transmitting the demo user ID. The client and server identity contracts are disconnected.
6. **Observation**: `chat_stream` executes Redis push and PostgreSQL write before yielding the first SSE token.
7. **Inference**: Under heavy database write loads or connection contention, TTFT directly degrades, creating perceived sluggishness.
8. **Observation**: PostgreSQL pool capacity is capped at 30 connections (`pool_size=10, max_overflow=20`) and Redis at 10 connections (`max_connections=10`).
9. **Inference**: Running 50 concurrent virtual users performing initial database writes will saturate the pool and trigger `PoolTimeoutError` unless the pool is increased or database operations are made non-blocking / mocked in load fixtures.
10. **Observation**: Running `npm test -- --run` returns `Error: Unknown argument: run` and `new-home.spec.ts` fails with `TS2305: Module '"./new-home"' has no exported member 'NewHome'`.
11. **Inference**: GitHub Actions frontend job will fail 100% of the time upon pull request, blocking automated delivery.

---

## 3. Caveats

1. **External LLM Quota**: Real LLM calls to Google Gemini or OpenAI during load tests (50 concurrent users) risk rate limits (HTTP 429) or token costs. Load tests must utilize the internal offline fallback or a mocked streaming generator to benchmark ASGI/FastAPI latency accurately.
2. **Database Test Environment**: Database connection pooling limits (30 connections) reflect the local PostgreSQL container configuration. In production cloud environments, PgBouncer or connection pooling proxies should be evaluated.
3. **Authentication Token Lifecycle**: Token refresh mechanisms (refresh tokens) are not currently implemented in `auth.py`; access tokens expire in 30 minutes without auto-refresh.

---

## 4. Conclusion

1. **Preliminary Plan Status**: `comprehensive_test_plan.md` has an exceptionally sound structure and complete test matrices (UI, SEC, LOAD, SAFE). To transition to `docs/comprehensive_test_plan.md`, it must be updated with:
   - Specific runner command fixes (`npm test -- --watch=false`).
   - Explicit file references for `backend/test/test_security_matrix.py` and `backend/test/test_load_concurrency.py`.
   - Concurrency pool remediation notes for 50 VUs.
2. **Security Vulnerability Remediations Required**:
   - Backend: Inject `current_user_id: str = Depends(get_current_user_id)` into all routes in `history.py`, `mood.py`, and `chat.py`. Enforce that callers can only query their own data unless assigned an admin role.
   - Frontend: Update `ChatService` and `MoodDataService` to inject `AuthService`, retrieve the active user ID (`authService.currentUser()?.id`), and attach `Authorization: Bearer ${token}` headers to all `fetch` requests.
3. **Load Testing Architecture**:
   - Tooling: Implement `backend/test/test_load_concurrency.py` using `httpx.AsyncClient` with `asyncio.gather` to launch 10 to 50 concurrent streaming sessions.
   - Measurement: Measure TTFT externally from request dispatch to receipt of the first SSE chunk; compute p50, p95, and p99 percentiles and error rates.
   - Tuning: Increase PostgreSQL `pool_size` and Redis `max_connections` in test environments to avoid pool starvation.
4. **CI/CD Pipeline Hardening**:
   - Fix line 66 of `.github/workflows/ci.yml`: change `npm test -- --run` to `npm test -- --watch=false`.
   - Fix `src/app/pages/new-home/new-home.spec.ts`: change `import { NewHome }` to `import { NewHomeComponent }`.
   - Add automated stages for SAST (`bandit`, `npm audit`), Security Matrix pytest, and Load concurrency verification.

---

## 5. Verification Method

### 5.1 Verifying the Vitest Execution Blockers
Run in PowerShell:
```powershell
# 1. Verify current failure on --run argument:
cd moodz-frontend
npm test -- --run
# Expected output: Error: Unknown argument: run

# 2. Verify current TypeScript compilation failure on NewHome import:
npx ng test --watch=false
# Expected output: TS2305: Module '"./new-home"' has no exported member 'NewHome'.
```

### 5.2 Verifying Backend Safety Gates & Normalization
Run in PowerShell:
```powershell
.\moodz\Scripts\pytest backend\test\evals\test_crisis_benchmark.py backend\test\evals\test_pii_scrubber.py backend\test\test_split_routes.py backend\test\test_normalization_logic.py -v
# Confirmed: All 9 tests pass in < 2.0 seconds with 100% recall on crisis triggers.
```

### 5.3 Verifying BOLA / IDOR Vulnerabilities
Run an unauthenticated HTTP request:
```powershell
# Query session history without Authorization header
curl -i -X GET "http://localhost:8000/api/chat-history/sessions?user_id=c47209cb-b2f1-4c76-a7ae-19805f3926b4"
# Vulnerable behavior: HTTP 200 OK with session data returned.
# Secure behavior: HTTP 401 Unauthorized ("Not authenticated").
```

### 5.4 Invalidation Conditions
- If `get_current_user_id` is adopted across all routers, any request without a valid JWT returning HTTP 200 invalidates the security audit.
- If `@angular/build:unit-test` is replaced with standard Vitest CLI (`vitest run`), the `--run` flag analysis becomes obsolete.
