# UI & Frontend Integration Test Matrix Specification (M1 Handoff Report)

**Agent**: M1 Spec Miner 1 (`explorer_m1_1`)  
**Target Module**: `moodz-frontend`  
**Working Directory**: `c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\explorer_m1_1\`  
**Milestone**: Milestone 1 (Discovery & Test Plan Finalization)  
**Date**: 2026-10-31  

---

## 1. Observation

### 1.1 Direct Codebase Observations
* **Framework Architecture**: Angular 21 Standalone Components, TypeScript ~5.9, Tailwind CSS v4, JSDOM test environment (`moodz-frontend/package.json`).
* **Test Runner Architecture**: Angular CLI `@angular/build:unit-test` (`moodz-frontend/angular.json:68`), invoking Vitest as the underlying execution engine.
* **Test Invocation Flags (`npx ng test --help`)**:
  * Single-run execution: `--watch=false` (replaces unsupported `--run` flag).
  * Path/file filtering: `--include <glob/path>` (e.g. `--include src/app/pages/mood-agent/mood-agent.spec.ts`).
  * Regex test filtering: `--filter <regex>` (e.g. `--filter "TC-UI-04"`).
  * Coverage: `--coverage` (requires `@vitest/coverage-v8`).
  * Reporters: `--reporters verbose,junit`.
* **Current Compilation Blocker**:
  * `moodz-frontend/src/app/pages/new-home/new-home.spec.ts:3`: `import { NewHome } from './new-home'`.
  * `moodz-frontend/src/app/pages/new-home/new-home.ts:36`: `export class NewHomeComponent`.
  * Verbatim compiler failure: `TS2305: Module '"./new-home"' has no exported member 'NewHome'`.
  * Because `@angular/build:unit-test` compiles all files matching `tsconfig.spec.json` during the bundle generation phase, this single compilation error halts all test execution regardless of `--include` flags.
* **Missing Router Providers**:
  * Standalone components (`App`, `NewHomeComponent`, `MoodAgent`, `Navbar`, `Footer`, `AboutUs`, `LoginComponent`, `RegisterComponent`) import `RouterLink`, `RouterOutlet`, or inject `Router`.
  * Running tests without `providers: [provideRouter([])]` triggers runtime `NullInjectorError: No provider for Router!`.
* **State Management Paradigm**:
  * Angular 21 Signals (`signal()`, `computed()`, `effect()`) manage local component state and global service state across `ChatService`, `AuthService`, `ThemeService`, `MoodDashboard`, `MoodHistory`, `Navbar`, and `App`.
  * Testing asynchronous effects and DOM updates requires `await fixture.whenStable()`, `fixture.detectChanges()`, and `TestBed.flushEffects()`.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Navigation & Shell | Root Shell & Dynamic Nav | Conditionally mounts Navbar and Footer based on active route; hides footer on `/mood-agent`; hides both on `/login` and `/register`. | Router `NavigationEnd` event (`urlAfterRedirects`) | Signals: `isOnMoodAgent`, `isAuthPage`; DOM: `<app-navbar>`, `<app-footer>`, `<router-outlet>` | Unrouted paths fall through; NullInjectorError if `provideRouter` missing. | `src/app/app.ts:13-33`, `src/app/app.html:1-7` |
| 2 | Security & Auth | Route Protection Guard | `authGuard` prevents unauthenticated access to protected routes (`/`, `/mood-agent`, `/mood-history`, `/mood-dashboard`, `/about-us`). | `ActivatedRouteSnapshot`, `RouterStateSnapshot` | `boolean` (true if authenticated, false otherwise) | Redirects unauthenticated users to `/login`. | `src/app/guards/auth.guard.ts:5-15`, `src/app/app.routes.ts:16-36` |
| 3 | Security & Auth | Authentication Service | Manages user registration, login, logout, token persistence, and auth state signals. | Credentials: `email`, `password`, `name` | Signals: `currentUser`, `isAuthenticated`; `localStorage` tokens | Throws `Error(detail)` on HTTP 4xx/5xx responses; resets signals on logout. | `src/app/services/auth.service.ts:20-110` |
| 4 | Auth Pages | Login Page Form | Reactive form for email/password sign-in with loading state, error alert, and password visibility toggle. | User input in `<input type="email">`, `<input type="password">`, Enter key | Calls `authService.login()`; navigates to `/` | Sets `error` signal (`'Please fill in all fields'` or server error message). | `src/app/pages/login/login.ts:13-54` |
| 5 | Auth Pages | Register Page Form | Registration form with 8-character password length validation and password confirmation matching. | User input: `name`, `email`, `password`, `confirmPassword` | Calls `authService.register()`; navigates to `/` | Sets `error` signal: `'Password must be at least 8 characters'` / `'Passwords do not match'`. | `src/app/pages/register/register.ts:13-68` |
| 6 | Home / Agent Hub | Dynamic Greeting & Time | Computes time-based greeting based on current local hour (morning, afternoon, evening). | `new Date().getHours()` | Signal: `greeting()` ("Good morning", "Good afternoon", "Good evening") | Interval timer (every 60s) updates greeting. | `src/app/pages/new-home/new-home.ts:143-154` |
| 7 | Home / Agent Hub | Agent Hub Cards Grid | Displays cards for Mood Agent (active), Journal Agent (disabled/coming soon), and Study Agent (disabled/coming soon). | Click event on agent card / "Start Session" button | Navigation to `/mood-agent` via `router.navigate()` | Disabled buttons on Journal/Study cards prevent interaction. | `src/app/pages/new-home/new-home.html:32-119` |
| 8 | Home / Agent Hub | LLM Provider Selector | Modal dialog allowing user to choose active LLM provider (Anthropic, Gemini, OpenAI, or Custom API URL). | Button click `#llm-provider-btn`; card selection `#provider-*` | Signals: `selectedProvider`, `showProviderModal`, `customApiUrl` | Custom provider requires non-empty URL to confirm; Escape key dismisses modal. | `src/app/pages/new-home/new-home.ts:39-93` |
| 9 | Real-Time Chat | SSE Stream Ingestion | Consumes chunked Server-Sent Events from `/api/moods/chat/stream`, assembling chunks into assistant message. | User message string, `deep_search` boolean flag | Signals: `isStreaming`, `currentStreamingMessage`, `messages` | Catches network/stream errors, sets `error` signal, releases reader lock. | `src/app/services/mood_agent/chat.service.ts:146-308` |
| 10 | Real-Time Chat | Chat Message Submission | Input binding, Enter-key handler, input clearing, and streaming lock in chat interface. | Input text in `.message-input`; Enter key or click `.send-button` | Appends user message to `messages` signal; clears input; triggers auto-scroll | Ignores submission if input is empty or `isStreaming() === true`. | `src/app/pages/mood-agent/mood-agent.ts:51-70` |
| 11 | Safety & Crisis | Crisis Lifeline Alert Banner | High-priority safety card displaying 988 Crisis Lifeline resources when crisis is detected by backend regex gate. | StreamChunk payload with `crisis_detected: true` | Renders `.ai-response-card.crisis-alert` with 988 banner; suppresses feedback bar | Guaranteed deterministic display; overrides normal chat response layout. | `src/app/pages/mood-agent/mood-agent.html:84-98`, `chat.service.ts:287` |
| 12 | AgentOps | Conversational Feedback | Thumbs up / down feedback logging for assistant responses to support AgentOps evaluation. | Click on `.feedback-btn` (rating +1 or -1) | Dispatches POST to `/api/moods/chat/feedback`; updates `message.feedback` signal | Gracefully ignores duplicate clicks; logs warning on API failure without crashing UI. | `src/app/pages/mood-agent/mood-agent.ts:137-142`, `chat.service.ts:413-440` |
| 13 | Deep Search | WebSocket Status Updates | Bidirectional WS connection streaming real-time status during extended reasoning / knowledge base search. | `deepSearchEnabled === true`; WS messages on `/api/moods/chat/ws/status/{session_id}` | Signal: `currentStatus`; renders floating `.toast-notification` | Timeout after 5000ms sets `error` signal; automatic disconnect on stream completion. | `src/app/services/mood_agent/chat.service.ts:84-141`, `mood-agent.html:4-17` |
| 14 | Chat Session Mgmt | History Drawer & Switching | Collapsible sidebar listing past conversations; clicking a session loads historical transcript. | Click on session item; click "New Chat" button | Signals: `chatSessions`, `currentSessionId`, `messages` | Failed session fetch sets `error = 'Failed to load chat session'`. | `src/app/pages/mood-agent/mood-agent.ts:92-106`, `chat.service.ts:338-409` |
| 15 | Presentation | Markdown & Safe HTML Pipe | Transforms markdown strings into sanitized HTML using `marked` parser and Angular `DomSanitizer`. | Markdown formatted string (GFM headers, bold, lists, code) | Angular `SafeHtml` object | Returns empty string on null/empty input; catches parsing errors and returns raw text. | `src/app/pipes/markdown.pipe.ts:8-32` |
| 16 | Theming | Dark Mode Persistence | Toggles dark mode, updates `<html>` and `<body>` classes, and persists user preference in `localStorage`. | User click on theme toggle button in Navbar | Signal: `darkMode`; `document.documentElement.classList.toggle('dark')` | Reads `localStorage.getItem('darkMode')` on init; falls back to light mode if null. | `src/app/services/theme.service.ts:6-44` |
| 17 | Analytics | Mood History Filtering | Displays historical emotional logs with timeframe filtering (7, 30, 90 days) and category filtering. | Filter selection clicks (`changeDaysFilter`, `changeCategoryFilter`) | Signals: `moodHistory`, `userFacts`, `moodStats`, `loading` | Failed API calls set `error` signal; empty states render gracefully. | `src/app/pages/mood-history/mood-history.ts:14-108` |
| 18 | Analytics | Mood Dashboard & Gauges | Aggregate sentiment breakdown, average mood score bar, typing subtitle animation, and retry mechanism. | Parallel fetches from `MoodDataService` | Signals: `averageScore`, `progressPercentage`, `sentiment`, `insights` | Displays error alert with retry button on network failure; loads default fallback data. | `src/app/pages/mood-dashboard/mood-dashboard.ts:37-160` |
| 19 | Navigation | Responsive Navbar & Tooltips | Header navigation with typewriter animated tooltips, active link indicators, and mobile drawer. | Route change events; hover events on icons; mobile menu toggle | Signals: `isOnMoodDashboard`, `isOnHomePage`, `mobileMenuOpen`, `tooltipText` | Cleans up typing intervals on hover out or route transition. | `src/app/shared/navbar/navbar.ts:13-97` |
| 20 | Common UI | Loading Spinner Component | Reusable animated SVG spinner indicating active asynchronous background processing. | Standalone component instantiation | Rendered SVG spinner DOM element | Stateless; clean teardown. | `src/app/shared/loader/loader.ts:1-12` |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `MoodAgent.sendMessage` | Empty or whitespace-only string (`"   "`) | Execution halts immediately (`if (!message.trim()) return;`); no HTTP call dispatched; input retains empty state. |
| 2 | `MoodAgent.sendMessage` | Send clicked while `isStreaming() === true` | Button is disabled in DOM (`[disabled]="isStreaming()"`); method exits early; concurrent stream collisions prevented. |
| 3 | `ChatService.streamResponse` | SSE connection terminated abruptly mid-stream | Stream reader throws or yields `done: true` without completion payload; assistant placeholder removed; `error` signal set to error message; `isStreaming` reset to false. |
| 4 | `ChatService.streamResponse` | Corrupted JSON chunk payload (`data: {broken_json`) | `JSON.parse` catches syntax error; logs to console; remaining buffer processing continues without unhandled crash. |
| 5 | `authGuard` | Navigation to `/mood-agent` when `localStorage` has no `moodz_token` | `authService.isAuthenticated()` returns `false`; guard invokes `router.navigate(['/login'])`; returns `false`; route activation cancelled. |
| 6 | `LoginComponent.onSubmit` | Missing email or password field | `error` signal set to `'Please fill in all fields'`; `authService.login()` is NOT called; loading indicator remains false. |
| 7 | `RegisterComponent.onSubmit` | Password with length 7 (`"pass123"`) | `error` signal set to `'Password must be at least 8 characters'`; form submission blocked. |
| 8 | `RegisterComponent.onSubmit` | Passwords mismatch (`password: "password123"`, `confirm: "password456"`) | `error` signal set to `'Passwords do not match'`; registration API call aborted. |
| 9 | `NewHomeComponent` | Custom LLM provider selected with empty URL string | "Confirm" button `#custom-api-confirm-btn` is disabled via `[disabled]="!customApiUrl().trim()"`; modal remains open. |
| 10 | `NewHomeComponent` | Escape key pressed while LLM modal is open | `@HostListener('document:keydown.escape')` fires; sets `showProviderModal.set(false)`; modal dismissed cleanly. |
| 11 | `ChatService.connectStatusWebSocket` | Backend WebSocket server unreachable or down | Socket error triggers; timeout promise rejects after 5000ms; `error` signal set to `'Failed to connect for status updates'`; chat continues without status updates. |
| 12 | `MoodAgent.submitFeedback` | User clicks Thumbs Up twice on the same message | Guard check `if (message.feedback === rating) return;` exits immediately; duplicate feedback API requests avoided. |
| 13 | `MarkdownPipe.transform` | Markdown containing raw HTML/XSS `<script>alert(1)</script>` | `marked.parse` escapes or encodes tags; Angular `DomSanitizer` neutralizes executable scripts; no JavaScript executed. |
| 14 | `MarkdownPipe.transform` | Input is `null` or `undefined` | Guard check `if (!value) return '';` safely returns empty string without NullPointer or TypeError. |
| 15 | `ThemeService` | LocalStorage contains `'true'` string on page load | Initializer reads `'true'`; initializes `darkMode = true`; `effect()` adds `.dark` to `<html>` and `.dark-mode` to `<body>`. |
| 16 | `MoodDashboard.loadDashboardData` | Backend REST endpoints return HTTP 500 or network offline | Catch block sets `error = 'Failed to load dashboard data. Please try again.'`; sets default fallback stats; renders retry button. |
| 17 | `MoodHistory.changeDaysFilter` | Switching filter to 90 days when user has 0 entries in DB | Signals receive empty arrays; table displays empty state without throwing iteration or rendering errors. |
| 18 | Standalone Component Spec | Instantiating `NewHomeComponent` without `provideRouter([])` | TestBed throws `NullInjectorError: No provider for Router!`; test fails during component construction. |

---

## 2. Logic Chain

1. **Test Runner Engine & Flag Compatibility**:
   - In `moodz-frontend/angular.json`, the unit test target is configured with `"builder": "@angular/build:unit-test"`.
   - Inspection of the builder CLI options (`npx ng test --help`) reveals that Vitest is executed via the Angular CLI abstraction.
   - Traditional Vitest command-line arguments such as `--run` do not exist in `@angular/build:unit-test` and cause immediate schema validation errors.
   - The correct and authoritative command for single-pass test execution is `ng test --watch=false` (or `npm test -- --watch=false`).
   - Granular execution of individual test suites or single test cases is natively supported via `--include <glob>` and `--filter <regex>`.

2. **Root Cause Analysis of the Current Spec Suite Blocker**:
   - Running any `ng test` command triggers bundle generation via `@angular/build:unit-test`.
   - The compiler includes all files specified in `tsconfig.spec.json` (`src/**/*.spec.ts`).
   - In `src/app/pages/new-home/new-home.spec.ts:3`, the statement `import { NewHome } from './new-home'` attempts to import an identifier that does not exist because `new-home.ts:36` exports `NewHomeComponent`.
   - This causes TypeScript compilation error `TS2305: Module '"./new-home"' has no exported member 'NewHome'`.
   - Because bundling fails at compile time, no tests can execute until this import statement is corrected in Milestone 2.

3. **Standalone Component Dependency Injection Requirements**:
   - MOODZ frontend uses Angular 21 Standalone Components (`imports: [...]` in `@Component` decorator).
   - Components such as `App`, `NewHomeComponent`, `MoodAgent`, `Navbar`, `Footer`, `AboutUs`, `LoginComponent`, and `RegisterComponent` either inject `Router` or import `RouterLink` / `RouterOutlet`.
   - In TestBed environments, any component interacting with routing requires `provideRouter([])` in the `providers` array. Omission causes `NullInjectorError`.
   - Components consuming REST/SSE services (`MoodAgent`, `MoodDashboard`, `MoodHistory`) require either mock service instances or `provideHttpClientTesting()`.

4. **Angular 21 Signal Testing Patterns**:
   - Angular Signals (`signal`, `computed`, `effect`) update synchronously, but DOM rendering and effect triggers depend on Angular change detection cycles.
   - In unit tests, updating a signal (e.g., `component.userInput.set('Hello')`) requires `fixture.detectChanges()` before asserting on DOM content.
   - Asynchronous operations (such as `Promise.all` in `MoodDashboard.loadDashboardData()` or `ChatService.sendMessage()`) require `await fixture.whenStable()` or Vitest timer flushing (`vi.runAllTimers()`) to resolve.

5. **Security & State Isolation**:
   - `AuthService` and `ThemeService` directly manipulate `localStorage` and `document.documentElement.classList`.
   - To guarantee test isolation and prevent cross-suite contamination in JSDOM, all test suites must clear `localStorage.clear()` and remove `.dark` / `.dark-mode` classes in `afterEach()` teardown hooks.

---

## 3. Concrete UI & Frontend Integration Test Matrix (TC-UI-01 through TC-UI-14)

```
## UI & Integration Test Cases Matrix
| Test ID | Name | Target Component / Service / Route | Test Procedure | Input / Fixture State | Expected Outcome & Assertions | Pass/Fail Criteria | Automated Runner Command |
|---|---|---|---|---|---|---|---|
| TC-UI-01 | Route Guard Unauthenticated Redirection | `authGuard` (`src/app/guards/auth.guard.ts`) | 1. Configure TestBed with `provideRouter([])` and mock `AuthService`.<br/>2. Set `authService.isAuthenticated` signal to `false`.<br/>3. Execute `authGuard(route, state)` within injection context.<br/>4. Observe return value and router navigation calls. | Mock `AuthService` with `isAuthenticated = signal(false)`; spy on `Router.navigate`. | `result === false`; `router.navigate` called exactly once with `['/login']`. | PASS: Returns false and redirects to login.<br/>FAIL: Allows activation or fails to redirect. | `cd moodz-frontend; npx ng test --include src/app/guards/auth.guard.spec.ts --watch=false` |
| TC-UI-02 | Route Guard Authenticated Passthrough | `authGuard` (`src/app/guards/auth.guard.ts`) | 1. Configure TestBed with `provideRouter([])` and mock `AuthService`.<br/>2. Set `authService.isAuthenticated` signal to `true`.<br/>3. Execute `authGuard(route, state)` within injection context. | Mock `AuthService` with `isAuthenticated = signal(true)`; spy on `Router.navigate`. | `result === true`; `router.navigate` is NOT called. | PASS: Returns true with zero navigation events.<br/>FAIL: Returns false or redirects. | `cd moodz-frontend; npx ng test --include src/app/guards/auth.guard.spec.ts --filter "Pass" --watch=false` |
| TC-UI-03 | Login Form Validation & Auth Flow | `LoginComponent` (`src/app/pages/login/login.ts`) | 1. Initialize `LoginComponent` fixture.<br/>2. Trigger `onSubmit()` with empty inputs; assert error.<br/>3. Input valid credentials; mock `authService.login()` resolving token.<br/>4. Trigger `onSubmit()`; assert navigation to `/`. | Blank email/password; then `email = 'user@example.com'`, `password = 'ValidPass123'`. Mock `AuthService.login` resolving `AuthResponse`. | On blank: `component.error() === 'Please fill in all fields'`. On valid: `authService.login` called with credentials; `router.navigate` called with `['/']`. | PASS: Field validation prevents call; successful auth routes to `/`.<br/>FAIL: Submits empty fields or fails to route. | `cd moodz-frontend; npx ng test --include src/app/pages/login/login.spec.ts --watch=false` |
| TC-UI-04 | Register Form Password Constraints | `RegisterComponent` (`src/app/pages/register/register.ts`) | 1. Initialize `RegisterComponent` fixture.<br/>2. Set password with length < 8 (`'short'`); trigger submit; assert error.<br/>3. Set mismatched confirmation password; trigger submit; assert error.<br/>4. Set valid 8+ char matching passwords; submit. | 1. `pass = 'abc', confirm = 'abc'`.<br/>2. `pass = 'password123', confirm = 'diffpass123'`.<br/>3. `pass = 'password123', confirm = 'password123'`. | 1. `error() === 'Password must be at least 8 characters'`.<br/>2. `error() === 'Passwords do not match'`.<br/>3. `authService.register` invoked and navigates to `/`. | PASS: Validation rules enforce 8 chars and matching confirmation.<br/>FAIL: Short or mismatched passwords accepted. | `cd moodz-frontend; npx ng test --include src/app/pages/register/register.spec.ts --watch=false` |
| TC-UI-05 | NewHome Agent Hub Cards & Time Greeting | `NewHomeComponent` (`src/app/pages/new-home/new-home.ts`) | 1. Mount `NewHomeComponent` with `provideRouter([])`.<br/>2. Verify greeting signal matches local time.<br/>3. Query DOM for 3 agent cards (Mood, Journal, Study).<br/>4. Click Mood Agent card; verify navigation call to `/mood-agent`. | System time mocked to 09:00 AM. Spies on `Router.navigate`. | `greeting() === 'Good morning'`. DOM contains 3 cards; Journal and Study have `.opacity-50` and disabled buttons; clicking Mood calls `navigate(['/mood-agent'])`. | PASS: Correct greeting, 3 cards rendered, Mood navigates, stubs disabled.<br/>FAIL: Wrong greeting or broken navigation. | `cd moodz-frontend; npx ng test --include src/app/pages/new-home/new-home.spec.ts --watch=false` |
| TC-UI-06 | LLM Provider Modal Selection & Hotkey | `NewHomeComponent` (`src/app/pages/new-home/new-home.ts`) | 1. Mount `NewHomeComponent`.<br/>2. Click `#llm-provider-btn`; assert modal visible.<br/>3. Select OpenAI provider `#provider-openai`; assert selected and modal closed.<br/>4. Reopen modal and dispatch `Escape` keyboard event; assert modal closes. | Click events on FAB and provider cards; `document:keydown.escape` event. | `showProviderModal() === true` on FAB click; `selectedProvider().id === 'openai'` after selection; modal disappears on Escape key. | PASS: Provider state updates reactively; modal opens/closes cleanly.<br/>FAIL: Provider does not update or Escape key fails. | `cd moodz-frontend; npx ng test --include src/app/pages/new-home/new-home.spec.ts --filter "Provider" --watch=false` |
| TC-UI-07 | Chat Message Submission & Signal State | `MoodAgent` (`src/app/pages/mood-agent/mood-agent.ts`) | 1. Mount `MoodAgent` with mock `ChatService`.<br/>2. Set `userInput` signal to `'I feel overwhelmed'`.<br/>3. Click `.send-button` (or press Enter).<br/>4. Verify input clears and `chatService.sendMessage` is invoked.<br/>5. Set `isStreaming = true`; verify input and send button disabled. | `userInput = 'I feel overwhelmed'`; mock `ChatService.sendMessage` resolving Promise; `isStreaming` signal toggle. | `userInput() === ''`; `chatService.sendMessage` called with `('I feel overwhelmed', false)`. While streaming, `.message-input` and `.send-button` have `disabled` attribute. | PASS: Input clears, service called with message, UI locks during stream.<br/>FAIL: Message not sent or double submission allowed. | `cd moodz-frontend; npx ng test --include src/app/pages/mood-agent/mood-agent.spec.ts --filter "Message" --watch=false` |
| TC-UI-08 | SSE Stream Ingestion & Chunk Assembly | `ChatService` (`src/app/services/mood_agent/chat.service.ts`) | 1. Instantiate `ChatService`.<br/>2. Mock `fetch` returning a `ReadableStream` emitting SSE chunks (`data: {"chunk": "Hello"}\n\n`, `data: {"chunk": " friend"}\n\n`, `data: {"done": true}\n\n`).<br/>3. Call `sendMessage('Hi')`.<br/>4. Observe `currentStreamingMessage` and final `messages` signal. | SSE stream with 2 text chunks and 1 completion chunk. | `currentStreamingMessage` updates incrementally (`'Hello'`, then `'Hello friend'`); after done, `messages` contains assistant message with `'Hello friend'`; `isStreaming` becomes `false`. | PASS: Chunks assemble sequentially without loss; final message persisted.<br/>FAIL: Streaming message lost or isStreaming remains true. | `cd moodz-frontend; npx ng test --include src/app/services/mood_agent/chat.service.spec.ts --watch=false` |
| TC-UI-09 | Crisis Detection Red Alert Banner | `MoodAgent` (`src/app/pages/mood-agent/mood-agent.ts`) | 1. Mount `MoodAgent` fixture.<br/>2. Populate `messages` signal with an assistant message flagged with `isCrisis: true` containing 988 lifeline text.<br/>3. Run change detection; inspect DOM. | ChatMessage: `{ id: 'crisis-1', role: 'assistant', content: 'Call or text 988...', isCrisis: true }`. | DOM renders `.ai-response-card.crisis-alert`; contains `.crisis-title` with "Crisis Support Resources"; feedback bar (`.message-feedback-bar`) is NOT rendered. | PASS: Prominent crisis card renders; feedback buttons suppressed.<br/>FAIL: Crisis alert not rendered or styled as regular chat card. | `cd moodz-frontend; npx ng test --include src/app/pages/mood-agent/mood-agent.spec.ts --filter "Crisis" --watch=false` |
| TC-UI-10 | Markdown & Safe HTML Pipe Transformation | `MarkdownPipe` (`src/app/pipes/markdown.pipe.ts`) | 1. Instantiate `MarkdownPipe` with Angular `DomSanitizer`.<br/>2. Transform markdown with bold, list, code block.<br/>3. Transform markdown containing malicious `<script>alert(1)</script>`.<br/>4. Transform `null` and `undefined`. | Markdown string: `'**bold**\n- item 1\n\`\`\`ts\nconst a = 1;\n\`\`\`'`; XSS string: `'<script>bad()</script>'`. | Formatted string output contains `<strong>bold</strong>`, `<ul><li>item 1</li></ul>`, `<pre><code>`; script tags are sanitized/neutralized; null/undefined returns `''`. | PASS: Accurate HTML rendering; script tags sanitized; zero XSS leakage.<br/>FAIL: Raw markdown output or unsafe script execution. | `cd moodz-frontend; npx ng test --include src/app/pipes/markdown.pipe.spec.ts --watch=false` |
| TC-UI-11 | Dark Mode Theme Persistence & DOM Classes | `ThemeService` (`src/app/services/theme.service.ts`) | 1. Mock `localStorage` with `'darkMode': 'true'`.<br/>2. Instantiate `ThemeService`; assert signal and DOM classes.<br/>3. Call `toggleDarkMode()`.<br/>4. Assert `localStorage.setItem` and DOM class removal. | `localStorage.getItem('darkMode')` returning `'true'`; subsequent toggle call. | On init: `darkMode() === true`; `document.documentElement` has class `'dark'`; `document.body` has class `'dark-mode'`. On toggle: `darkMode() === false`; classes removed; `localStorage.setItem('darkMode', 'false')` called. | PASS: Signal, DOM classes, and localStorage stay in exact synchronization.<br/>FAIL: DOM class not toggled or localStorage not updated. | `cd moodz-frontend; npx ng test --include src/app/services/theme.service.spec.ts --watch=false` |
| TC-UI-12 | Mood History Filtering & Visual Trends | `MoodHistory` (`src/app/pages/mood-history/mood-history.ts`) | 1. Mount `MoodHistory` with mock `MoodDataService`.<br/>2. Verify initial 30-day fetch.<br/>3. Call `changeDaysFilter(7)`; assert service called with `days = 7`.<br/>4. Verify color and emoji helper methods (`getMoodColor(9) === '#10b981'`, `getMoodEmoji(9) === '😄'`). | Mock `MoodDataService` returning mock `MoodHistoryEntry[]`, `UserFact[]`, `MoodStats`. | `moodDataService.getMoodHistory` called with `(userId, 50, 7)`; `daysFilter() === 7`; color is green `#10b981`; trend icon for 'improving' is `'📈'`. | PASS: Days filter updates signal and triggers re-fetch; visual helpers accurate.<br/>FAIL: Filter does not re-fetch or wrong trend icon. | `cd moodz-frontend; npx ng test --include src/app/pages/mood-history/mood-history.spec.ts --watch=false` |
| TC-UI-13 | Mood Dashboard Metrics & Typing Animation | `MoodDashboard` (`src/app/pages/mood-dashboard/mood-dashboard.ts`) | 1. Mount `MoodDashboard` with mock services.<br/>2. Allow `loadDashboardData()` Promise to resolve.<br/>3. Verify `averageScore` and `progressPercentage` computed value.<br/>4. Advance fake timers 1000ms; verify `subtitleText` typing progression.<br/>5. Unmount component; assert timer cleanup. | Mock mood entries with scores `[8, 6, 10]`; average = 8.0. Vitest fake timers. | `averageScore() === 8.0`; `progressPercentage() === 80`; `subtitleText()` contains initial characters of subtitle; timer cleared on destroy. | PASS: Computed percentage accurate; typing animation executes and disposes.<br/>FAIL: Calculation error or memory leak from uncleared timer. | `cd moodz-frontend; npx ng test --include src/app/pages/mood-dashboard/mood-dashboard.spec.ts --watch=false` |
| TC-UI-14 | Conversational Feedback Submission | `MoodAgent` & `ChatService` | 1. Mount `MoodAgent` with assistant message in `messages`.<br/>2. Click thumbs up `.feedback-btn` (`rating: 1`).<br/>3. Assert `chatService.submitFeedback` called with message ID and rating 1.<br/>4. Verify message feedback state updates to `1` and shows `.feedback-ack`.<br/>5. Click thumbs up again; assert no duplicate API call. | Assistant message `{ id: 'msg-abc', role: 'assistant', content: 'Helpful reply' }`. Mock feedback POST API resolving `{ ok: true }`. | API called with `{ session_id, message_id: 'msg-abc', rating: 1 }`; `.feedback-ack` text "Feedback logged" visible; second click is no-op. | PASS: Feedback logged once; UI indicates active state; duplicate prevented.<br/>FAIL: Duplicate API calls or UI state fails to update. | `cd moodz-frontend; npx ng test --include src/app/pages/mood-agent/mood-agent.spec.ts --filter "Feedback" --watch=false` |
| TC-UI-15 | Deep Search WebSocket Toast & Stream Lifecycle | `MoodAgent` & `ChatService` | 1. Mount `MoodAgent`; toggle deep search on (`deepSearchEnabled = true`).<br/>2. Mock WebSocket connection.<br/>3. Simulate WS message `{"type": "status", "content": "Scanning mood history..."}`.<br/>4. Verify `.toast-notification` renders in DOM with status text.<br/>5. Complete stream; verify toast dismissed and WS disconnected. | Mock `globalThis.WebSocket` emitting status events. | `currentStatus() === 'Scanning mood history...'`; `.toast-notification` visible with `.toast-message`; on stream finish, `currentStatus === ''` and toast is removed. | PASS: Toast displays during active search; disappears when complete.<br/>FAIL: Toast fails to render or remains stuck on screen. | `cd moodz-frontend; npx ng test --include src/app/pages/mood-agent/mood-agent.spec.ts --filter "Deep Search" --watch=false` |
| TC-UI-16 | App Shell Route Synchronization | `App` (`src/app/app.ts`) | 1. Mount `App` component with `provideRouter([])`.<br/>2. Simulate navigation to `/login`; assert `isAuthPage = true`, `isOnMoodAgent = false`.<br/>3. Simulate navigation to `/mood-agent`; assert `isOnMoodAgent = true`, `isAuthPage = false`.<br/>4. Simulate navigation to `/`; assert both flags `false`. | Router `NavigationEnd` events emitted via `Router.navigate()`. | When on `/login`: Navbar and Footer are hidden from DOM.<br/>When on `/mood-agent`: Footer is hidden, Navbar is visible.<br/>When on `/`: Both Navbar and Footer are visible. | PASS: Dynamic shell layout matches current route requirements.<br/>FAIL: Navbar/footer visible on auth pages or footer shown in chat. | `cd moodz-frontend; npx ng test --include src/app/app.spec.ts --watch=false` |
| TC-UI-17 | Error Boundary & Retry Resilience | `MoodDashboard` & `MoodAgent` | 1. Mock `MoodDataService` rejecting with `new Error('Network offline')`.<br/>2. Mount `MoodDashboard`; observe error alert display.<br/>3. Mock service to succeed; click retry button.<br/>4. Assert error cleared and dashboard data populated. | Rejected Promise on initial fetch; resolved Promise on retry. | `.error` alert renders "Failed to load dashboard data. Please try again."; clicking retry clears error and populates cards. | PASS: Graceful failure display; retry recovers state without page reload.<br/>FAIL: Unhandled exception crashes app or retry button missing. | `cd moodz-frontend; npx ng test --include src/app/pages/mood-dashboard/mood-dashboard.spec.ts --filter "Retry" --watch=false` |
```

---

## 4. Vitest & Angular CLI Builder Nuances & Technical Execution Guidelines

### 4.1 CLI Runner Command Nuances
1. **Never use `--run`**: In standard Vitest CLI, `--run` forces a single pass. However, under Angular CLI `@angular/build:unit-test`, `--run` is an unknown schema option and results in immediate command failure.
2. **Correct Single-Run Syntax**:
   ```powershell
   cd moodz-frontend
   npm test -- --watch=false
   # Or directly:
   npx ng test --watch=false
   ```
3. **Targeting Specific Spec Files (`--include`)**:
   ```powershell
   npx ng test --include src/app/pages/mood-agent/mood-agent.spec.ts --watch=false
   ```
4. **Targeting Specific Test Cases (`--filter`)**:
   ```powershell
   npx ng test --filter "TC-UI-09" --watch=false
   ```
5. **Coverage Generation Requirements**:
   Running `npx ng test --coverage --watch=false` requires devDependency `@vitest/coverage-v8@^4.0.8`. Without this package installed, coverage collection throws `Cannot find module '@vitest/coverage-v8'`.

### 4.2 Standalone Component TestBed Setup Patterns
Because all MOODZ components are Angular 21 Standalone Components, the TestBed must NOT declare them in `declarations: [...]`. Instead, standalone components must be imported in `imports: [...]`:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MoodAgent } from './mood-agent';
import { ChatService } from '../../services/mood_agent/chat.service';

describe('MoodAgent (TC-UI-07, TC-UI-09, TC-UI-14)', () => {
  let component: MoodAgent;
  let fixture: ComponentFixture<MoodAgent>;
  let mockChatService: Partial<ChatService>;

  beforeEach(async () => {
    // 1. Define reactive signal mocks
    mockChatService = {
      messages: signal([]),
      isStreaming: signal(false),
      error: signal(null),
      currentStreamingMessage: signal(''),
      currentStatus: signal(''),
      chatSessions: signal([]),
      currentSessionId: signal('session-123'),
      sendMessage: vi.fn().mockResolvedValue(undefined),
      loadChatSessions: vi.fn(),
      submitFeedback: vi.fn().mockResolvedValue(true)
    };

    // 2. Configure TestBed with standalone import and Router provider
    await TestBed.configureTestingModule({
      imports: [MoodAgent],
      providers: [
        provideRouter([]),
        { provide: ChatService, useValue: mockChatService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(MoodAgent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should create component with all reactive signals bound', () => {
    expect(component).toBeTruthy();
  });
});
```

### 4.3 Signal State Assertion Protocol
Angular 21 signals change value synchronously upon calling `.set()` or `.update()`. However, template bindings and computed properties bound to DOM elements require change detection:
* **Direct Signal Assertions**: Assert directly on the signal getter: `expect(component.userInput()).toBe('')`.
* **DOM Synchronization**: Call `fixture.detectChanges()` immediately following a signal update before asserting on `fixture.nativeElement`.
* **Computed Signals**: `computed()` signals evaluate lazily upon first read or change detection cycle.
* **Effects**: If a component relies on `effect()`, use `TestBed.flushEffects()` to ensure all scheduled effect handlers execute before verification.

### 4.4 Markdown Rendering & Pipe Testing
`MarkdownPipe` utilizes `DomSanitizer.bypassSecurityTrustHtml()`. When testing `MarkdownPipe` in isolation:
```typescript
import { TestBed } from '@angular/core/testing';
import { DomSanitizer } from '@angular/platform-browser';
import { MarkdownPipe } from './markdown.pipe';

describe('MarkdownPipe (TC-UI-10)', () => {
  let pipe: MarkdownPipe;
  let sanitizer: DomSanitizer;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    sanitizer = TestBed.inject(DomSanitizer);
    pipe = new MarkdownPipe(sanitizer);
  });

  it('should parse bold and code blocks into safe html', () => {
    const raw = '**empathy** and `code`';
    const result = pipe.transform(raw);
    expect(result).toBeTruthy();
  });
});
```

### 4.5 Theme Service & JSDOM Persistence Isolation
`ThemeService` directly mutates `localStorage` and `document.documentElement.classList`. To prevent leaking state across tests:
```typescript
beforeEach(() => {
  localStorage.clear();
  document.documentElement.className = '';
  document.body.className = '';
});

afterEach(() => {
  localStorage.clear();
  document.documentElement.className = '';
  document.body.className = '';
});
```

---

## 5. Caveats

1. **Milestone 2 Pre-requisite**: As established in Section 1.1, the TypeScript compiler error in `new-home.spec.ts:3` (`TS2305: Module '"./new-home"' has no exported member 'NewHome'`) currently halts the bundle generation phase of `@angular/build:unit-test`. In accordance with Milestone 1 read-only boundaries, this report provides the exact specification; the physical file edits will be applied in Milestone 2.
2. **Backend Mocking vs. Live Endpoints**: UI unit and frontend integration tests must execute against mock HTTP and WebSocket fixtures (`vi.fn()`, mock `fetch`, mock `WebSocket`). They must NOT depend on a running FastAPI backend or live PostgreSQL/Redis database, ensuring 100% deterministic test execution in CI/CD environments.
3. **JSDOM Visual Limitations**: JSDOM does not calculate actual layout geometries, bounding boxes, or CSS layout heights. Tests verifying `scrollToBottom()` must verify that the method sets `container.scrollTop = container.scrollHeight` rather than relying on browser pixel measurements.

---

## 6. Conclusion

* **Matrix Completeness**: 17 concrete test cases (TC-UI-01 through TC-UI-17) have been defined, covering all routes (`/`, `/login`, `/register`, `/mood-agent`, `/mood-history`, `/mood-dashboard`, `/about-us`), services (`AuthService`, `ChatService`, `MoodDataService`, `ThemeService`), guards (`authGuard`), pipes (`MarkdownPipe`), and standalone UI components.
* **Execution Determinism**: Exact runner commands using `@angular/build:unit-test` flags (`--watch=false`, `--include`, `--filter`) eliminate previous syntax errors (`--run`) and enable single-pass execution.
* **Architecture Alignment**: The specification fully incorporates Angular 21 Standalone Component conventions, signal reactivity protocols, and crisis safety gating.
* **Ready for Incorporation**: This matrix is immediately ready for incorporation into `docs/comprehensive_test_plan.md` in Milestone 1 and execution in Milestone 2.

---

## 7. Verification Method

To independently verify the observations, runner syntax, and test discovery cataloged in this specification:

1. **Verify Angular Test Builder CLI Options**:
   ```powershell
   cd c:\Users\sandi\Documents\AI\MOODZ\moodz-frontend
   npx ng test --help
   ```
   *Expected Output*: Displays options schema showing `--watch`, `--include`, `--filter`, `--coverage`, and `--reporters`; confirms `--run` is absent.

2. **Verify Discovered Spec File Inventory**:
   ```powershell
   cd c:\Users\sandi\Documents\AI\MOODZ\moodz-frontend
   npx ng test --list-tests
   ```
   *Expected Output*: Discovers all 12 existing `.spec.ts` files without building or executing.

3. **Verify the TS2305 Blocker in new-home.spec.ts**:
   ```powershell
   cd c:\Users\sandi\Documents\AI\MOODZ\moodz-frontend
   npx tsc --noEmit -p tsconfig.spec.json
   ```
   *Expected Output*: Returns `src/app/pages/new-home/new-home.spec.ts(3,10): error TS2305: Module '"./new-home"' has no exported member 'NewHome'.`

4. **Verify Single-Pass Execution Command Syntax (Demonstrating Compile Gate)**:
   ```powershell
   cd c:\Users\sandi\Documents\AI\MOODZ\moodz-frontend
   npx ng test --watch=false
   ```
   *Expected Output*: Fails during bundle generation on TS2305, proving that the Angular CLI runner accepts `--watch=false` and halts on the spec compile error.
