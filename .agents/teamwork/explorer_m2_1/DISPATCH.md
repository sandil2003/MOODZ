## 2026-10-31T04:21:22Z
You are Explorer M2-1 (Frontend Vitest Blocker Remediation Explorer) in Milestone 2 of the MOODZ testing project.
Your working directory is: c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\explorer_m2_1\
Mandatory reading:
1. c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\orchestrator_1\PROJECT.md
3. docs/comprehensive_test_plan.md

Objective:
Formulate the exact, verifiable remediation steps for the frontend Vitest test suite in `moodz-frontend`:
1. Fix `src/app/pages/new-home/new-home.spec.ts:3`: replace `import { NewHome } from './new-home'` with `import { NewHomeComponent } from './new-home'` and update `NewHome` -> `NewHomeComponent` across the file.
2. Fix `src/app/app.spec.ts`: update the stale test expectation that checks for `<h1>Hello, moodz-frontend</h1>` since `app.html` has no `<h1>`. Verify what assertions correctly validate `App` component mounting (e.g. checking title signal or router-outlet existence).
3. Ensure all routed standalone components (`App`, `NewHomeComponent`, `MoodAgent`, `Navbar`, etc.) have `provideRouter([])` in their TestBed configuration.
4. Update `moodz-frontend/package.json` test script: configure `"test": "ng test --watch=false"`.
5. Test command verification: Verify that `npm test` runs cleanly and all frontend tests pass without errors.

Output Requirements:
Save your complete remediation blueprint to: c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\explorer_m2_1\handoff.md
Send a completion message to caller when done.
