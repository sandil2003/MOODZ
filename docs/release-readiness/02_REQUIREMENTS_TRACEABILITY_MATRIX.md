# 📊 02 - Requirements Traceability Matrix (RTM)

> **Document ID:** RTM-MOODZ-1.0.0  
> **Status:** Baselined for Pre-Production Release Verification  
> **System:** MOODZ AI Mental Wellness Platform  
> **Traceability Standard:** ISO/IEC/IEEE 29148:2018 (Requirements Engineering)  

---

## 1. Overview & Purpose

The **Requirements Traceability Matrix (RTM)** establishes strict bidirectional traceability between Product Requirements, System Architecture Components, Verification Test Cases, and Production Acceptance Gates. 

In healthcare and clinical AI applications, an auditable RTM is an industry prerequisite for:
1. Ensuring that every user-facing and safety requirement is verified by designated automated or manual tests.
2. Preventing feature bloat or untested code paths from entering production.
3. Enabling fast root-cause analysis and defect regression tracking.

---

## 2. Requirements Traceability Table

| Req ID | Category | Requirement Description | Architecture Module / File Path | Test Case ID | Test Level & Method | Criticality | Production Acceptance Threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-SAF-01** | **Safety** | Deterministic detection of suicidal ideation & self-harm signals with zero-latency bypass to 988 Lifeline. | `app/services/crisis_detector.py`<br/>`app/services/mood_graph.py` | `TC-CRISIS-001`<br/>`TC-CRISIS-002` | Automated Pytest Benchmark (`test_crisis_benchmark.py`) | **P0 (Blocker)** | **100% Recall (0 False Negatives)** across 25+ trigger corpus; execution time $< 10\text{ms}$. |
| **REQ-SAF-02** | **Safety** | Absolute prohibition of unauthorized medical/psychiatric diagnoses and drug prescribing. | `app/services/mood_agent.py`<br/>`app/services/fallback_mocks.py` | `TC-AI-SAFE-001` | Automated DeepEval & Regex heuristics (`test_empathy_evals.py`) | **P0 (Blocker)** | **0 occurrences** of disallowed diagnostic or prescriptive phrases. |
| **REQ-SAF-03** | **Safety** | Empathetic emotional validation without toxic positivity or dismissive responses. | `app/services/mood_graph.py`<br/>System Prompts | `TC-AI-SAFE-002` | DeepEval LLM-as-a-Judge (`test_empathy_evals.py`) | **P1 (Critical)** | Mean Empathy Score $\ge 0.85 / 1.00$; zero dismissive phrases. |
| **REQ-PRIV-01** | **Privacy** | Sub-millisecond recursive redaction of PII (Email, Phone, SSN, Credit Card) before telemetry export. | `app/core/pii_scrubber.py`<br/>`app/core/telemetry.py` | `TC-PII-001`<br/>`TC-PII-002` | Automated Unit & Integration (`test_pii_scrubber.py`) | **P0 (Blocker)** | **100% masking** of sensitive patterns; 0 raw PII leaked into Arize Phoenix spans. |
| **REQ-CHAT-01** | **Functional** | Real-time Server-Sent Events (SSE) streaming chat with chunked token delivery. | `app/routes/chat.py`<br/>`moodz-frontend/src/app/services/chat.service.ts` | `TC-CHAT-001` | Automated API & Contract Test (`test_chat_stream.html` / Pytest) | **P1 (Critical)** | Smooth SSE chunk stream; terminal `[DONE]` signal; zero hanging connections. |
| **REQ-CHAT-02** | **Functional** | Multi-agent coordination with LangGraph StateGraph engine and Google ADK tool bindings. | `app/agents/mood_adk.py`<br/>`app/services/mood_graph.py` | `TC-AGENT-001`<br/>`TC-AGENT-002` | Integration Test (`test_adk_hybrid_agent.py`) | **P1 (Critical)** | Deterministic state transitions; proper tool routing and fallback execution. |
| **REQ-MEM-01** | **Functional** | Multi-tier context memory retrieval: Redis short-term history buffer & Pinecone episodic memory. | `app/services/session_manager.py`<br/>`app/services/vector_service.py` | `TC-MEM-001`<br/>`TC-MEM-002` | Integration Test (`test_split_routes.py`) | **P1 (Critical)** | Relevant past memories injected within token budget ($< 1500$ tokens); $< 100\text{ms}$ retrieval. |
| **REQ-AUTH-01** | **Security** | Secure user registration, authentication, bcrypt password hashing, and JWT bearer token issuance. | `app/routes/auth.py`<br/>`app/core/auth_utils.py` | `TC-AUTH-001`<br/>`TC-AUTH-002` | Automated Unit & API (`test_split_routes.py`) | **P0 (Blocker)** | Zero plain-text passwords; JWT expiration enforced; unauthorized requests rejected (401). |
| **REQ-MOOD-01** | **Functional** | Daily mood recording, tag classification, sentiment scoring, and historical trend aggregation. | `app/routes/mood.py`<br/>`app/routes/history.py`<br/>`app/models.py` | `TC-MOOD-001`<br/>`TC-MOOD-002` | Integration & UI E2E (`test_split_routes.py` / Angular) | **P2 (Major)** | Mood entries persisted to PostgreSQL; analytics graph renders accurate averages. |
| **REQ-OPS-01** | **Observability** | Self-hosted AgentOps tracing, tool execution logging, and Human-in-the-Loop (HITL) rating persistence. | `app/core/telemetry.py`<br/>`app/routes/chat.py` (`/feedback`) | `TC-OPS-001`<br/>`TC-OPS-002` | Integration Test (`test_telemetry_export.py`) | **P2 (Major)** | Every chat turn generates Phoenix span; user thumbs up/down updates trace metadata. |
| **REQ-PERF-01** | **Performance** | Low latency conversational response with Time-to-First-Token (TTFT) under interactive threshold. | Architecture End-to-End | `TC-PERF-001` | Load Test Suite (k6 / Locust) | **P1 (Critical)** | P95 TTFT $\le 800\text{ms}$; sustained token streaming rate $\ge 25\text{ tokens/sec}$. |
| **REQ-PERF-02** | **Performance** | High concurrency scalability under peak multi-user load without degradation. | Azure Container Apps / FastAPI Async | `TC-PERF-002` | Concurrency Load Test (500 CCU) | **P1 (Critical)** | Error rate $< 0.1\%$; CPU $< 75\%$; Memory leak free over 1 hour soak test. |
| **REQ-REL-01** | **Reliability** | Zero-downtime database schema migration and backward-compatible rollback capability. | `backend/alembic/` | `TC-REL-001` | Staging Migration Rehearsal | **P0 (Blocker)** | `alembic upgrade head` and `alembic downgrade -1` succeed cleanly with zero data loss. |

---

## 3. Verification Coverage Summary

```
Total Requirements Baselined: 13
├── Safety & Compliance:      3 (100% Automated Coverage)
├── Privacy & Security:       2 (100% Automated Coverage)
├── Functional & AI Agents:   4 (100% Automated / Integration Coverage)
├── Performance & Scale:      2 (Automated Load Test Coverage)
├── Observability & HITL:     1 (Integration & Trace Coverage)
└── Release & DB Reliability: 1 (Staging Rehearsal Coverage)

Coverage Status: 100% of Functional and Non-Functional Requirements are mapped to test suites.
```

---

## 4. Requirement Verification Sign-Off

* **Requirements Analyst / Product Owner:** __________________________ Date: _____________
* **Quality Assurance Lead:** __________________________ Date: _____________
* **System Architect:** __________________________ Date: _____________
