# Comprehensive Frontend & Vitest Survey Handoff Report

**Agent**: Explorer 1 (Frontend & Vitest Explorer)  
**Target Module**: `moodz-frontend`  
**Working Directory**: `c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\explorer_survey_1\`  
**Date**: 2026-10-31  

---

## 1. Observation

### 1.1 Test Configuration & Discovery
* **Package Manager & Scripts (`moodz-frontend/package.json`)**:
  ```json
  "scripts": {
    "ng": "ng",
    "start": "ng serve",
    "build": "ng build",
    "watch": "ng build --watch --configuration development",
    "test": "ng test"
  },
  "devDependencies": {
    "@angular/build": "^21.0.1",
    "@angular/cli": "^21.0.1",
    "@angular/compiler-cli": "^21.0.0",
    "@tailwindcss/postcss": "^4.1.12",
    "jsdom": "^27.1.0",
    "postcss": "^8.5.3",
    "tailwindcss": "^4.1.12",
    "typescript": "~5.9.2",
    "vitest": "^4.0.8"
  }
  ```
* **Angular Builder Configuration (`moodz-frontend/angular.json`)**:
  ```json
  "test": {
    "builder": "@angular/build:unit-test"
  }
  ```
  `@angular/build:unit-test` uses Vitest as its default runner (`enum: ["karma", "vitest"]`, default: `"vitest"`). Options default to `watch: true` in interactive/TTY sessions.
* **TypeScript Spec Configuration (`moodz-frontend/tsconfig.spec.json`)**:
  ```json
  {
    "extends": "./tsconfig.json",
    "compilerOptions": {
      "outDir": "./out-tsc/spec",
      "types": ["vitest/globals"]
    },
    "include": [
      "src/**/*.d.ts",
      "src/**/*.spec.ts"
    ]
  }
  ```
* **Discovered Test Files (`npx ng test --list-tests`)**:
  1. `src/app/app.spec.ts`
  2. `src/app/pages/about-us/about-us.spec.ts`
  3. `src/app/pages/home/home.spec.ts`
  4. `src/app/pages/journal-agent/journal-agent.spec.ts`
  5. `src/app/pages/mood-agent/mood-agent.spec.ts`
  6. `src/app/pages/mood-dashboard/mood-dashboard.spec.ts`
  7. `src/app/pages/new-home/new-home.spec.ts`
  8. `src/app/pages/study-agent/study-agent.spec.ts`
  9. `src/app/services/mood_agent/mood.spec.ts`
  10. `src/app/shared/footer/footer.spec.ts`
  11. `src/app/shared/loader/loader.spec.ts`
  12. `src/app/shared/navbar/navbar.spec.ts`

### 1.2 The Vitest Import Blocker (`new-home.spec.ts`)
* **Execution Command**:
  `cd moodz-frontend; npm test -- --watch=false`
* **Verbatim Build Error Output**:
  ```
  > moodz-frontend@0.0.0 test
  > ng test --watch=false

  > Building...
  √ Building...
  Application bundle generation failed. [4.305 seconds] - 2026-10-31T03:41:02.733Z

  X [ERROR] TS2305: Module '"./new-home"' has no exported member 'NewHome'. [plugin angular-compiler]

      src/app/pages/new-home/new-home.spec.ts:3:9:
        3 │ import { NewHome } from './new-home';
          ╵          ~~~~~~~
  ```
* **Direct TypeScript Compiler Verification**:
  `cd moodz-frontend; npx tsc --noEmit -p tsconfig.spec.json`
  Output:
  `src/app/pages/new-home/new-home.spec.ts(3,10): error TS2305: Module '"./new-home"' has no exported member 'NewHome'.`
* **File Code Inspection**:
  * In `moodz-frontend/src/app/pages/new-home/new-home.spec.ts`:
    ```typescript
    3: import { NewHome } from './new-home';
    5: describe('NewHome', () => {
    6:   let component: NewHome;
    7:   let fixture: ComponentFixture<NewHome>;
    11:     imports: [NewHome]
    15:     fixture = TestBed.createComponent(NewHome);
    ```
  * In `moodz-frontend/src/app/pages/new-home/new-home.ts`:
    ```typescript
    36: export class NewHomeComponent {
    ```
  * In `moodz-frontend/src/app/app.routes.ts`:
    ```typescript
    15: loadComponent: () => import('./pages/new-home/new-home').then(m => m.NewHomeComponent),
    ```
  `new-home.ts` exports `NewHomeComponent`, but `new-home.spec.ts` imports the non-existent identifier `NewHome`.

### 1.3 Direct Vitest CLI Execution Diagnostics
* **Command**: `cd moodz-frontend; npx vitest run`
  * **Result**: Exits with code 1; 12/12 suites fail with `ReferenceError: describe is not defined` because globals are not imported and no `vitest.config.ts` sets `test.globals = true`.
* **Command**: `cd moodz-frontend; npx vitest run --globals`
  * **Result**: Exits with code 1; 12/12 suites fail with:
    `Error: Need to call TestBed.initTestEnvironment() first`
    `Error: Component 'App' is not resolved: - templateUrl: ./app.html - styleUrl: ./app.css. Did you run and wait for 'resolveComponentResources()' ?`
* **Runner Root Cause**:
  Raw Vitest cannot execute Angular standalone components out-of-the-box without Angular's compiler pipeline. The intended test runner is Angular CLI's `@angular/build:unit-test` via `npm test` or `ng test`.

### 1.4 Downstream Stale & Broken Test Expectations
* **`moodz-frontend/src/app/app.spec.ts`**:
  ```typescript
  17:   it('should render title', async () => {
  18:     const fixture = TestBed.createComponent(App);
  19:     await fixture.whenStable();
  20:     const compiled = fixture.nativeElement as HTMLElement;
  21:     expect(compiled.querySelector('h1')?.textContent).toContain('Hello, moodz-frontend');
  22:   });
  ```
  * Inspection of `src/app/app.html`:
    ```html
    @if (!isAuthPage()) {
    <app-navbar></app-navbar>
    }
    <router-outlet />
    @if (!isOnMoodAgent() && !isAuthPage()) {
    <app-footer></app-footer>
    }
    ```
    There is no `<h1>` element in `app.html`. Line 21 will fail with `Cannot read property 'textContent' of null/undefined`.
* **Missing Router Providers**:
  `App`, `Home`, `NewHomeComponent`, `Navbar`, `Footer`, `AboutUs`, and `MoodAgent` all inject `Router` or import `RouterLink` / `RouterModule`. The existing spec files for these components do not include `providers: [provideRouter([])]`.

### 1.5 Frontend Hardcoded User IDs & Auth Architecture Disconnect
* **Hardcoded Demo User ID**:
  `moodz-frontend/src/app/services/mood_agent/chat.service.ts`:
  ```typescript
  58:     // IMPORTANT: Using the demo user that exists in the database
  59:     // This is the user_id created by create_demo_user.py
  60:     // For production, replace this with actual user authentication
  61:     private readonly DEMO_USER_ID = 'c47209cb-b2f1-4c76-a7ae-19805f3926b4';
  62: 
  63:     // User and Session IDs
  64:     private userId: string = this.DEMO_USER_ID;
  ```
* **Hardcoded ID Propagation**:
  1. `chat.service.ts:216`: Chat streaming request sends body: `{ user_id: this.userId, session_id: this.sessionId, message, deep_search }`.
  2. `chat.service.ts:341`: Chat history sessions query: `${this.API_BASE_URL}/api/chat-history/sessions?user_id=${this.userId}`.
  3. `chat.service.ts:369`: Chat session detail query: `${this.API_BASE_URL}/api/chat-history/sessions/${sessionId}?user_id=${this.userId}`.
  4. `mood-dashboard.ts:111`: `const userId = this.chatService.getUserId();` passed to `moodDataService.getMoodHistory(userId, 10, 7)`, `getUserFacts(userId, ...)`, and `getMoodStats(userId, 7)`.
  5. `mood-history.ts:38`: `const userId = this.chatService.getUserId();` passed to `moodDataService.getMoodHistory(userId, 50, days)`, `getUserFacts(...)`, and `getMoodStats(...)`.
* **Auth Layer Disconnect & Security Vulnerability**:
  * `AuthService` (`src/app/services/auth.service.ts`) logs in users, stores tokens in `localStorage` under `moodz_token`, and user details under `moodz_user`.
  * `authGuard` (`src/app/guards/auth.guard.ts`) verifies `authService.isAuthenticated()`.
  * **However**, neither `ChatService` nor `MoodDataService` injects `AuthService`! Neither service attaches the JWT bearer token (`Authorization: Bearer <token>`) to HTTP/fetch requests.
  * Every authenticated user ends up reading and writing data under the single hardcoded user ID `c47209cb-b2f1-4c76-a7ae-19805f3926b4`. This is also a Broken Object Level Authorization (BOLA/IDOR) vulnerability on the backend endpoints which trust client-supplied user IDs without session/token verification.

### 1.6 Architectural Catalog: UI Pages, Components, Services, and Routing

| Category | Name | File Path | Route / Selector | Purpose & Key Features |
|---|---|---|---|---|
| **Root Shell** | `App` | `src/app/app.ts` | `<app-root>` | Root layout; monitors route changes; conditionally renders navbar/footer; mounts router-outlet. |
| **Auth Page** | `LoginComponent` | `src/app/pages/login/login.ts` | `/login` | Email/password sign-in form; communicates with `AuthService.login()`; password visibility toggle; error alerts. |
| **Auth Page** | `RegisterComponent` | `src/app/pages/register/register.ts` | `/register` | Account registration; validates password length (>=8) and password confirmation; calls `AuthService.register()`. |
| **Main Page** | `NewHomeComponent` | `src/app/pages/new-home/new-home.ts` | `/` (`canActivate: [authGuard]`) | Authenticated home dashboard; time-based greeting; agent cards (Mood, Journal, Study); LLM provider selection modal (Anthropic, Gemini, OpenAI, Custom); typewriter mood tooltip. |
| **Agent Page** | `MoodAgent` | `src/app/pages/mood-agent/mood-agent.ts` | `/mood-agent` (`authGuard`) | AI companion chat; SSE stream reading; WebSocket deep search status; thumbs up/down feedback; crisis alerts; chat session drawer. |
| **Dashboard Page** | `MoodDashboard` | `src/app/pages/mood-dashboard/mood-dashboard.ts` | `/mood-dashboard` (`authGuard`) | Sentiment overview; average mood gauge; recent logs; user insights/facts; typing subtitle animation; error retry. |
| **History Page** | `MoodHistory` | `src/app/pages/mood-history/mood-history.ts` | `/mood-history` (`authGuard`) | Detailed mood logs; timeframe filtering (7, 30, 90 days); category filter; sentiment emojis and trend icons (`📈`, `📉`, `➡️`). |
| **Info Page** | `AboutUs` | `src/app/pages/about-us/about-us.ts` | `/about-us` (`authGuard`) | Mission statement and team background; typewriter title animation. |
| **Legacy Page** | `Home` | `src/app/pages/home/home.ts` | `<app-home>` (unrouted) | Legacy landing page with draggable geometric elements and `activateAgent()` router trigger. |
| **Stub Page** | `JournalAgent` | `src/app/pages/journal-agent/journal-agent.ts` | (unrouted stub) | Empty component stub for future journaling agent. |
| **Stub Page** | `StudyAgent` | `src/app/pages/study-agent/study-agent.ts` | (unrouted stub) | Empty component stub for future study assistant agent. |
| **Shared** | `Navbar` | `src/app/shared/navbar/navbar.ts` | `<app-navbar>` | Header navigation bar; active route detection; dark mode toggle via `ThemeService`; animated tooltips; mobile drawer. |
| **Shared** | `Footer` | `src/app/shared/footer/footer.ts` | `<app-footer>` | Footer navigation links; copyright year; collapsible mobile link accordions. |
| **Shared** | `Loader` | `src/app/shared/loader/loader.ts` | `<app-loader>` | Loading spinner component. |
| **Service** | `AuthService` | `src/app/services/auth.service.ts` | `providedIn: 'root'` | Manages user registration, login, logout, token persistence in `localStorage`, and auth signals. |
| **Service** | `ChatService` | `src/app/services/mood_agent/chat.service.ts` | `providedIn: 'root'` | Manages SSE streaming chat (`/api/moods/chat/stream`), WebSocket status updates, session history, AgentOps feedback, and demo user ID. |
| **Service** | `MoodDataService` | `src/app/services/mood_agent/mood-data.service.ts` | `providedIn: 'root'` | REST client for mood history, user facts, and aggregate mood stats. |
| **Service** | `ThemeService` | `src/app/services/theme.service.ts` | `providedIn: 'root'` | Manages dark mode preference in `localStorage` and toggles `.dark` / `.dark-mode` CSS classes on `<html>` / `<body>`. |
| **Service** | `Mood` | `src/app/services/mood_agent/mood.ts` | `providedIn: 'root'` | Empty boilerplate service. |
| **Guard** | `authGuard` | `src/app/guards/auth.guard.ts` | CanActivateFn | Route guard verifying `authService.isAuthenticated()`; redirects to `/login`. |
| **Pipe** | `MarkdownPipe` | `src/app/pipes/markdown.pipe.ts` | `markdown` | Transforms markdown to sanitized safe HTML using `marked` and `DomSanitizer`. |

### 1.7 Existing Test Coverage & Gaps
* **Current Coverage Metric**:
  * Total functional units: 21 (14 components, 5 services, 1 guard, 1 pipe).
  * Existing test files: 12.
  * Existing unit tests executing actual logic: **0**. All 12 spec files contain solely initial scaffold assertions (`expect(component).toBeTruthy()`).
* **Completely Missing Spec Files (0% Coverage)**:
  1. `src/app/services/auth.service.spec.ts` (AuthService)
  2. `src/app/services/mood_agent/chat.service.spec.ts` (ChatService)
  3. `src/app/services/mood_agent/mood-data.service.spec.ts` (MoodDataService)
  4. `src/app/services/theme.service.spec.ts` (ThemeService)
  5. `src/app/guards/auth.guard.spec.ts` (authGuard)
  6. `src/app/pipes/markdown.pipe.spec.ts` (MarkdownPipe)
  7. `src/app/pages/login/login.spec.ts` (LoginComponent)
  8. `src/app/pages/register/register.spec.ts` (RegisterComponent)
  9. `src/app/pages/mood-history/mood-history.spec.ts` (MoodHistory)
* **Missing Test Tooling Dependency**:
  `@vitest/coverage-v8` is not present in `devDependencies`. Running `ng test --coverage` will error without it.

---

## 2. Logic Chain

1. **Test Failure Mechanism**:
   * Direct inspection of `moodz-frontend/src/app/pages/new-home/new-home.spec.ts:3` revealed `import { NewHome } from './new-home'`.
   * Inspection of `moodz-frontend/src/app/pages/new-home/new-home.ts:36` revealed `export class NewHomeComponent`.
   * When `ng test` runs, `@angular/build:unit-test` invokes the Angular TypeScript compiler over all files matching `tsconfig.spec.json` (`src/**/*.spec.ts`).
   * The compiler halts on `TS2305: Module '"./new-home"' has no exported member 'NewHome'`.
   * Because esbuild bundling fails on compilation error, **zero tests are executed**, blocking the entire testing pipeline.

2. **Runner Architecture Diagnosis**:
   * Running `npx vitest run` directly fails because Angular components require Ahead-Of-Time (AOT) template compilation, style resolution, and Angular TestBed test environment initialization (`TestBed.initTestEnvironment`).
   * `@angular/build:unit-test` encapsulates this build and initialization pipeline.
   * Therefore, running unit tests must be executed through Angular CLI: `ng test --watch=false` or `npm test -- --watch=false`.

3. **Stale Assertions & Dependency Injection**:
   * After the TS2305 compilation error is resolved, tests for components that inject `Router` (`App`, `NewHomeComponent`, `Navbar`, etc.) will fail at runtime if `provideRouter([])` is not supplied.
   * `app.spec.ts` will fail because it asserts the presence of `<h1>Hello, moodz-frontend</h1>` which does not exist in `app.html`.

4. **Authentication & IDOR Flaw**:
   * In `chat.service.ts:61`, `DEMO_USER_ID = 'c47209cb-b2f1-4c76-a7ae-19805f3926b4'` is hardcoded.
   * `chat.service.ts` and `mood-data.service.ts` issue HTTP requests with `?user_id=${this.userId}` or path parameters without using `AuthService` or attaching the JWT token from `localStorage`.
   * Therefore, authentication in the UI is purely decorative: logging in as any user still accesses demo user `c47209cb-b2f1-4c76-a7ae-19805f3926b4`, and any user ID can be manipulated in requests without backend authorization checks.

---

## 3. Caveats

1. **Read-Only Investigation**: As an Explorer agent, no source code in `moodz-frontend` was modified during this survey.
2. **Backend Coupling**: End-to-end integration of `ChatService` and `MoodDataService` requires the FastAPI backend (`http://localhost:8000`) and PostgreSQL to be running. In unit test suites, these HTTP and WebSocket calls must be mocked (`provideHttpClientTesting()` or mocking `globalThis.fetch` and `globalThis.WebSocket`).
3. **Legacy Files**: `Home` (`src/app/pages/home/home.ts`) is currently unrouted because `/` routes to `NewHomeComponent`. It remains in the project and is compiled into tests unless explicitly removed or excluded.

---

## 4. Conclusion & Recommended Remediation Strategies

### Blocker Remediation 1: Fix `new-home.spec.ts`
Update `moodz-frontend/src/app/pages/new-home/new-home.spec.ts` to import `NewHomeComponent` and provide `provideRouter([])`:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { NewHomeComponent } from './new-home';

describe('NewHomeComponent', () => {
  let component: NewHomeComponent;
  let fixture: ComponentFixture<NewHomeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewHomeComponent],
      providers: [provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(NewHomeComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
```

### Blocker Remediation 2: Fix `app.spec.ts`
Update `moodz-frontend/src/app/app.spec.ts` to include `provideRouter([])` and remove the obsolete `h1` check:

```typescript
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should have title signal initialized', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect((app as any).title()).toBe('moodz-frontend');
  });
});
```

### Blocker Remediation 3: Add `provideRouter([])` to Component Specs
Add `providers: [provideRouter([])]` to:
* `src/app/pages/about-us/about-us.spec.ts`
* `src/app/pages/home/home.spec.ts`
* `src/app/shared/navbar/navbar.spec.ts`
* `src/app/shared/footer/footer.spec.ts`
* `src/app/pages/mood-agent/mood-agent.spec.ts`

### Blocker Remediation 4: Package.json Scripts & Coverage Dependencies
1. Update `moodz-frontend/package.json` scripts:
   ```json
   "test": "ng test --watch=false",
   "test:watch": "ng test",
   "test:coverage": "ng test --watch=false --coverage"
   ```
2. Add `@vitest/coverage-v8` to `devDependencies`:
   ```bash
   npm install --save-dev @vitest/coverage-v8@^4.0.8
   ```

### Remediation 5: Connect `ChatService` and `MoodDataService` to `AuthService`
1. Inject `AuthService` into `ChatService`:
   ```typescript
   private authService = inject(AuthService);
   ```
2. Derive `userId` dynamically from `this.authService.currentUser()?.id`.
3. Include HTTP header `Authorization: Bearer ${this.authService.getToken()}` on all fetch requests in `ChatService` and `MoodDataService`.
4. Ensure the backend FastAPI endpoints validate the JWT token instead of blindly trusting client query/path parameters (remediating BOLA/IDOR).

---

## 5. Verification Method

To independently verify these findings:

1. **Verify the TS2305 Import Blocker**:
   ```powershell
   cd c:\Users\sandi\Documents\AI\MOODZ\moodz-frontend
   npx tsc --noEmit -p tsconfig.spec.json
   ```
   *Expected Outcome*: Exact error `TS2305: Module '"./new-home"' has no exported member 'NewHome'` in `new-home.spec.ts:3:10`.

2. **Verify Test Runner Behavior**:
   ```powershell
   cd c:\Users\sandi\Documents\AI\MOODZ\moodz-frontend
   npm test -- --watch=false
   ```
   *Expected Outcome*: Fails during bundle generation with the TS2305 error.

3. **Verify Discovered Test Inventory**:
   ```powershell
   cd c:\Users\sandi\Documents\AI\MOODZ\moodz-frontend
   npx ng test --list-tests
   ```
   *Expected Outcome*: Prints exactly the 12 spec files cataloged in Section 1.1.

4. **Verify Hardcoded User ID**:
   ```powershell
   cd c:\Users\sandi\Documents\AI\MOODZ\moodz-frontend
   Select-String -Path "src/app/services/mood_agent/chat.service.ts" -Pattern "c47209cb"
   ```
   *Expected Outcome*: Matches `private readonly DEMO_USER_ID = 'c47209cb-b2f1-4c76-a7ae-19805f3926b4';` on line 61.
