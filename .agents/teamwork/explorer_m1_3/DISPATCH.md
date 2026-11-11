## 2026-10-31T03:54:10Z
You are M1 Spec Miner 3 (Security & Load Testing Matrix Specification) in Milestone 1 of the MOODZ testing project.
Your working directory is: c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\explorer_m1_3\

Mandatory inputs to read:
1. c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\orchestrator_1\PROJECT.md
3. Preliminary plan: C:\Users\sandi\.gemini\antigravity\brain\b1b115c5-4e5e-4005-bef2-4ddea0005453\comprehensive_test_plan.md
4. Explorer 3 handoff report: c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\explorer_survey_3\handoff.md

Objective:
Specify the exact, concrete test matrices for:
1. Security & Vulnerability Testing (TC-SEC-01 through TC-SEC-12+):
   - Detailed specifications for testing BOLA/IDOR on `/api/chat-history/sessions` and `/sessions/{session_id}`
   - BOLA/IDOR on `/api/mood-data/mood-history/{user_id}`, `/user-facts/{user_id}`, and `/mood-stats/{user_id}`
   - User identity decoupling on `/api/moods/chat/stream`
   - Hardcoded frontend DEMO_USER_ID and missing Bearer auth
   - JWT signature tampering, expired tokens, SQLi, XSS, CORS, rate limiting
2. Load & Concurrency Testing (TC-LOAD-01 through TC-LOAD-06+):
   - 50 Concurrent Virtual Users streaming load harness (`backend/test/test_load_concurrency.py`)
   - Measuring Time-To-First-Token (TTFT) and total latency percentiles (p50, p95, p99)
   - Database connection pool saturation handling (`pool_size=10, max_overflow=20`) and Redis pool constraints
   - Pass/fail SLA criteria (e.g. TTFT < 1500ms, 0% drop rate, error rate < 1%)

For each test case specify: Test ID, Name, Target Module, Step-by-Step Procedure, Fixture State, Expected Outcome, Pass/Fail Criteria, and Execution Command.

Output Requirements:
Save your complete specification report to: c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\explorer_m1_3\handoff.md
Send a completion message to caller with a summary.
