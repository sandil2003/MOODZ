# Project: MOODZ Comprehensive Testing & Quality Engineering

## Architecture
- **Frontend**: Angular 21 Standalone Components, TypeScript ~5.9, Tailwind CSS v4, Vitest via `@angular/build:unit-test` (`ng test --watch=false`).
- **Backend**: FastAPI 0.162, SQLAlchemy 2.0 Async (asyncpg + PostgreSQL `moodz_db`), Redis 7 (session caching), LangGraph + Google ADK agentic engine with deterministic regex safety gate (`CrisisDetector`) and asynchronous profiler.
- **Test Infrastructure**:
  - Frontend: `@angular/build:unit-test` (Vitest engine).
  - Backend: Pytest 9.1.1, pytest-asyncio, deepeval, Phoenix / OpenTelemetry.
  - Security & Load: Custom pytest-based security authorization matrix (`backend/test/test_security_matrix.py`) and asyncio/httpx-based 50 VU streaming load harness (`backend/test/test_load_concurrency.py`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Test Plan & Matrices Specification | Full test plan update in docs/comprehensive_test_plan.md covering UI, Security, Load, AI Safety, Unit, Integration | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Vitest Suite Blocker Remediation | Fix TS2305 in new-home.spec.ts, fix app.spec.ts, router providers, runner command | M2 | ORIGINAL_REQUEST §R2 |
| 3 | Pytest Suite Blocker Remediation | Add pytest.ini (asyncio_mode=auto), remediate stale scripts, run full backend test battery | M2 | ORIGINAL_REQUEST §R2 |
| 4 | Crisis & Safety Benchmark Execution | Execute 100% deterministic crisis detection benchmark (<10ms SLA) and PII scrubber tests | M2 | ORIGINAL_REQUEST §R2 |
| 5 | Security Suite & BOLA/IDOR Verification | Author and execute test_security_matrix.py validating BOLA/IDOR across history, mood, chat endpoints | M3 | ORIGINAL_REQUEST §R2, R3 |
| 6 | 50 VU Streaming Load & TTFT Testing | Author and execute test_load_concurrency.py measuring TTFT, latency percentiles (p50/p95/p99), error rate | M3 | ORIGINAL_REQUEST §R2, R3 |
| 7 | Test Results Report & Coverage Metrics | Generate docs/comprehensive_test_results_report.md with quantitative pass/fail and coverage breakdown | M4 | ORIGINAL_REQUEST §R3 |
| 8 | Security Audit & Remediation Specs | Document BOLA/IDOR, hardcoded demo user ID, missing Bearer headers with architectural fix design | M4 | ORIGINAL_REQUEST §R3 |
| 9 | CI/CD Pipeline Gap Analysis | Evaluate existing pipeline, runner syntax failures, and define required CI/CD additions | M4 | ORIGINAL_REQUEST §R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey & Codebase Exploration | Full codebase & test infra survey | none | DONE |
| M1 | Comprehensive Master Test Plan | Author docs/comprehensive_test_plan.md (81 concrete test cases) | M0 | DONE |
| M2 | Blocker Remediation & Execution | Vitest 12/12 files passed; Pytest 23 passed, 1 skipped | M1 | DONE |
| M3 | Security & 50 VU Load Testing | test_security_matrix.py (20/20 passed), test_load_concurrency.py (8/8 passed) | M2 | DONE |
| M4 | Comprehensive Test Results Report | Author docs/comprehensive_test_results_report.md & CI/CD Gap Analysis | M3 | DONE |

## Code Layout & Primary Artifacts
- `docs/comprehensive_test_plan.md`: Authoritative Master Test Plan (1,708 lines, 81 test cases across 8 disciplines)
- `moodz-frontend/src/app/pages/new-home/new-home.spec.ts`: Remediated frontend spec (TS2305 fix)
- `moodz-frontend/src/app/app.spec.ts`: Remediated frontend spec (router-outlet & title assertions)
- `moodz-frontend/package.json`: Configured `"test": "ng test --watch=false"`
- `backend/pytest.ini`: Root and backend pytest configuration (`asyncio_mode = auto`)
- `backend/test/test_security_matrix.py`: Security test suite (TC-SEC-01..20)
- `backend/test/test_load_concurrency.py`: Concurrency & TTFT load test suite (TC-LOAD-01..08)
- `docs/comprehensive_test_results_report.md`: Executive-ready comprehensive test results report & CI/CD gap analysis (1,072 lines)
