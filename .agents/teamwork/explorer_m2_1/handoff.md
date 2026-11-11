# Milestone 2 — Frontend Vitest Blocker Remediation Blueprint

## 1. Observation

### Observation 1.1: Direct Compilation Blocker in `new-home.spec.ts`
When executing the test suite via `npx ng test --watch=false`, the Angular CLI `@angular/build:unit-test` builder fails at bundle generation:
```
> Building...
√ Building...
Application bundle generation failed. [3.738 seconds] - 2026-10-31T04:24:44.184Z

X [ERROR] TS2305: Module '"./new-home"' has no exported member 'NewHome'. [plugin angular-compiler]

    src/app/pages/new-home/new-home.spec.ts:3:9:
      3 │ import { NewHome } from './new-home';
        ╵          ~~~~~~~
```
Inspecting `moodz-frontend/src/app/pages/new-home/new-home.ts` (lines 35-37):
```typescript
35: })
36: export class NewHomeComponent {
37:   private router = inject(Router);
```
`new-home.ts` exports `NewHomeComponent`, whereas `new-home.spec.ts` (lines 3-15) imports and instantiates the non-existent symbol `NewHome`:
```typescript
3: import { NewHome } from './new-home';
...
6:   let component: NewHome;
7:   let fixture: ComponentFixture<NewHome>;
...
11:       imports: [NewHome]
...
15:     fixture = TestBed.createComponent(NewHome);
```
Because `tsconfig.spec.json` includes `src/**/*.spec.ts` in compilation, this single TS2305 error blocks the bundling of the entire test suite, preventing any test from running.

### Observation 1.2: Stale Assertion in `app.spec.ts`
Inspecting `moodz-frontend/src/app/app.spec.ts` (lines 17-22):
```typescript
17:   it('should render title', async () => {
18:     const fixture = TestBed.createComponent(App);
19:     await fixture.whenStable();
20:     const compiled = fixture.nativeElement as HTMLElement;
21:     expect(compiled.querySelector('h1')?.textContent).toContain('Hello, moodz-frontend');
22:   });
```
However, inspecting `moodz-frontend/src/app/app.html` (lines 1-7):
```html
1: @if (!isAuthPage()) {
2: <app-navbar></app-navbar>
3: }
4: <router-outlet />
5: @if (!isOnMoodAgent() && !isAuthPage()) {
6: <app-footer></app-footer>
7: }
```
`app.html` does not contain any `<h1>` element. Consequently, `compiled.querySelector('h1')` returns `null`, and `expect(null?.textContent).toContain(...)` fails.
Furthermore, in `moodz-frontend/src/app/app.ts` (lines 13-17):
```typescript
13: export class App implements OnInit {
14:   protected readonly title = signal('moodz-frontend');
15:   isOnMoodAgent = signal<boolean>(false);
16:   isAuthPage = signal<boolean>(false);
17:   private router = inject(Router);
```
`App` manages title state via a protected reactive signal `title = signal('moodz-frontend')` and injects `Router`.

### Observation 1.3: Missing `provideRouter([])` Across Standalone Components
The following components inject `Router` or render router directives (`RouterOutlet`, `RouterLink`, `RouterLinkActive`), but their corresponding `.spec.ts` files omit `providers: [provideRouter([])]` from `TestBed.configureTestingModule`:
1. `App` (`src/app/app.ts:17` injects `Router`, renders `<router-outlet />`, `<app-navbar>`, `<app-footer>`).
2. `NewHomeComponent` (`src/app/pages/new-home/new-home.ts:37` injects `Router`).
3. `MoodAgent` (`src/app/pages/mood-agent/mood-agent.ts:6,10` imports `RouterModule`).
4. `Navbar` (`src/app/shared/navbar/navbar.ts:2,9,24` injects `Router`, imports `RouterLink`, `RouterLinkActive`).
5. `Footer` (`src/app/shared/footer/footer.ts:2,6` imports `RouterLink`).
6. `Home` (`src/app/pages/home/home.ts:2,15` injects `Router`).
7. `AboutUs` (`src/app/pages/about-us/about-us.ts:2,6` imports `RouterLink`).

In Angular 21, instantiating any standalone component with unprovided router dependencies throws:
```
NullInjectorError: R3InjectorError(DynamicTestModule)[Router -> Router]: 
  NullInjectorError: No provider for Router!
```

### Observation 1.4: Runner Configuration Discrepancy in `package.json`
Inspecting `moodz-frontend/package.json` (lines 4-10):
```json
4:   "scripts": {
5:     "ng": "ng",
6:     "start": "ng serve",
7:     "build": "ng build",
8:     "watch": "ng build --watch --configuration development",
9:     "test": "ng test"
10:   },
```
The test script runs `ng test`. By default, `@angular/build:unit-test` launches in interactive file watcher mode (`watch=true`), causing CI and batch commands to hang indefinitely.
Additionally, passing `--run` (standard in standalone Vitest CLI) triggers an Angular CLI schema validation error:
```
Schema validation failed with the following errors:
  Data path "" must NOT have additional properties(run).
```
The valid Angular CLI flag for single-pass non-interactive execution is `--watch=false`.

### Observation 1.5: Interval Timers in `AboutUs` and `MoodDashboard`
- `AboutUs` (`src/app/pages/about-us/about-us.ts:28`): Launches `setInterval(..., 50)` on `ngOnInit()`.
- `MoodDashboard` (`src/app/pages/mood-dashboard/mood-dashboard.ts:83`): Launches `setInterval(..., 30)` on `ngOnInit()`.
Both components implement `ngOnDestroy()` with `clearInterval`. In test fixtures, unless `fixture.destroy()` is called in `afterEach()`, active timers can cause asynchronous leakage or Vitest teardown warnings.

---

## 2. Logic Chain

1. **Step 1 (Compilation Resolution)**:
   - *From Observation 1.1*: `new-home.spec.ts` imports symbol `NewHome` which is undefined in `new-home.ts`.
   - *Deduction*: Updating the import to `import { NewHomeComponent } from './new-home'` and replacing all occurrences of `NewHome` with `NewHomeComponent` resolves TS2305.
   - *Impact*: The Angular TypeScript compiler successfully builds the test bundle, allowing test execution to begin.

2. **Step 2 (App Mounting & Title Assertion)**:
   - *From Observation 1.2*: `app.html` contains no `<h1>` tag; it renders `<app-navbar>`, `<router-outlet />`, and `<app-footer>`.
   - *Deduction*: Checking `compiled.querySelector('h1')` will always return `null`. Valid assertions for component creation and template layout must verify:
     1. Component instance truthiness: `expect(app).toBeTruthy()`.
     2. Signal state: `expect((app as any).title()).toBe('moodz-frontend')`.
     3. Structural template elements: `expect(compiled.querySelector('router-outlet')).toBeTruthy()` and `expect(compiled.querySelector('app-navbar')).toBeTruthy()`.

3. **Step 3 (Dependency Injection Hardening via `provideRouter([])`)**:
   - *From Observation 1.3*: `App`, `NewHomeComponent`, `MoodAgent`, `Navbar`, `Footer`, `Home`, and `AboutUs` inject `Router` or use `RouterLink`/`RouterOutlet`.
   - *Deduction*: Adding `import { provideRouter } from '@angular/router'` and `providers: [provideRouter([])]` to the `TestBed.configureTestingModule` calls in all 7 spec files satisfies Angular DI.
   - *Impact*: Prevents `NullInjectorError: No provider for Router!` across the entire suite.

4. **Step 4 (Test Script Non-Interactive Execution)**:
   - *From Observation 1.4*: The default `ng test` command hangs in watch mode, and passing `--run` causes builder schema rejection.
   - *Deduction*: Configuring `"test": "ng test --watch=false"` in `moodz-frontend/package.json` ensures `npm test` runs all tests once and exits with code 0 on success.

5. **Step 5 (Fixture Teardown Isolation)**:
   - *From Observation 1.5*: `AboutUs` and `MoodDashboard` start interval timers in `ngOnInit()`.
   - *Deduction*: Adding `afterEach(() => { fixture?.destroy(); });` to `about-us.spec.ts` and `mood-dashboard.spec.ts` invokes `ngOnDestroy()`, clearing intervals and preventing asynchronous timer leaks.

---

## 3. Caveats

1. **Backend Integration Independence**:
   - `MoodAgent` and `MoodDashboard` communicate with backend endpoints (`http://localhost:8000`). Both components implement defensive error handling (`try/catch`) and signal fallbacks (`setDefaultValues()`), ensuring unit tests pass even when the backend is offline.
2. **Missing Spec Files for Un-tested Components**:
   - The current repository contains 12 spec files. Pages such as `LoginComponent`, `RegisterComponent`, and `MoodHistory` currently have no `.spec.ts` files. Adding test coverage for those is specified in `docs/comprehensive_test_plan.md` under Matrix 1 (TC-UI-01 through TC-UI-17) for future expansion.
3. **No Direct Production Source Code Edits**:
   - In adherence to the Teamwork Explorer read-only role, no source files were directly modified during this investigation. All remediation steps are delivered as machine-applicable patch files and replacement files in `.agents/teamwork/explorer_m2_1/`.

---

## 4. Conclusion & Concrete Remediation Blueprint

### Summary of Changes Required

| Target File | Change Description | Impact |
|---|---|---|
| `moodz-frontend/package.json` | Update `"test": "ng test"` to `"test": "ng test --watch=false"` | Enables clean single-run execution without hanging in watch mode |
| `moodz-frontend/src/app/pages/new-home/new-home.spec.ts` | Replace `NewHome` -> `NewHomeComponent`, add `provideRouter([])` | Fixes TS2305 blocker and Router DI |
| `moodz-frontend/src/app/app.spec.ts` | Replace stale `<h1>` assertion with signal & DOM assertions, add `provideRouter([])` | Fixes assertion failure and Router DI |
| `moodz-frontend/src/app/shared/navbar/navbar.spec.ts` | Add `provideRouter([])` to providers | Resolves `NullInjectorError: No provider for Router!` |
| `moodz-frontend/src/app/shared/footer/footer.spec.ts` | Add `provideRouter([])` to providers | Resolves `NullInjectorError: No provider for Router!` |
| `moodz-frontend/src/app/pages/home/home.spec.ts` | Add `provideRouter([])` to providers | Resolves `NullInjectorError: No provider for Router!` |
| `moodz-frontend/src/app/pages/mood-agent/mood-agent.spec.ts` | Add `provideRouter([])` to providers | Resolves `NullInjectorError: No provider for Router!` |
| `moodz-frontend/src/app/pages/about-us/about-us.spec.ts` | Add `provideRouter([])` to providers and `afterEach` teardown | Resolves Router DI and interval leak |
| `moodz-frontend/src/app/pages/mood-dashboard/mood-dashboard.spec.ts` | Add `provideRouter([])` to providers and `afterEach` teardown | Resolves Router DI and interval leak |

---

### Detailed Code Modifications

#### 1. `moodz-frontend/package.json`
```json
// BEFORE (line 9):
    "test": "ng test"

// AFTER (line 9):
    "test": "ng test --watch=false"
```

#### 2. `moodz-frontend/src/app/pages/new-home/new-home.spec.ts`
```typescript
// BEFORE:
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NewHome } from './new-home';

describe('NewHome', () => {
  let component: NewHome;
  let fixture: ComponentFixture<NewHome>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewHome]
    })
    .compileComponents();

    fixture = TestBed.createComponent(NewHome);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

// AFTER:
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

#### 3. `moodz-frontend/src/app/app.spec.ts`
```typescript
// BEFORE:
import { TestBed } from '@angular/core/testing';
import { App } from './app';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render title', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('Hello, moodz-frontend');
  });
});

// AFTER:
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

  it('should have the title signal initialized to moodz-frontend', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect((app as any).title()).toBe('moodz-frontend');
  });

  it('should render router-outlet and navbar', async () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('router-outlet')).toBeTruthy();
    expect(compiled.querySelector('app-navbar')).toBeTruthy();
  });
});
```

#### 4. `moodz-frontend/src/app/shared/navbar/navbar.spec.ts`
```typescript
// AFTER:
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Navbar } from './navbar';

describe('Navbar', () => {
  let component: Navbar;
  let fixture: ComponentFixture<Navbar>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Navbar],
      providers: [provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Navbar);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
```

#### 5. `moodz-frontend/src/app/shared/footer/footer.spec.ts`
```typescript
// AFTER:
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Footer } from './footer';

describe('Footer', () => {
  let component: Footer;
  let fixture: ComponentFixture<Footer>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Footer],
      providers: [provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Footer);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
```

#### 6. `moodz-frontend/src/app/pages/home/home.spec.ts`
```typescript
// AFTER:
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Home } from './home';

describe('Home', () => {
  let component: Home;
  let fixture: ComponentFixture<Home>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Home],
      providers: [provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Home);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
```

#### 7. `moodz-frontend/src/app/pages/mood-agent/mood-agent.spec.ts`
```typescript
// AFTER:
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { MoodAgent } from './mood-agent';

describe('MoodAgent', () => {
  let component: MoodAgent;
  let fixture: ComponentFixture<MoodAgent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MoodAgent],
      providers: [provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MoodAgent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
```

#### 8. `moodz-frontend/src/app/pages/about-us/about-us.spec.ts`
```typescript
// AFTER:
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AboutUs } from './about-us';

describe('AboutUs', () => {
  let component: AboutUs;
  let fixture: ComponentFixture<AboutUs>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AboutUs],
      providers: [provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AboutUs);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    fixture?.destroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
```

#### 9. `moodz-frontend/src/app/pages/mood-dashboard/mood-dashboard.spec.ts`
```typescript
// AFTER:
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { MoodDashboard } from './mood-dashboard';

describe('MoodDashboard', () => {
  let component: MoodDashboard;
  let fixture: ComponentFixture<MoodDashboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MoodDashboard],
      providers: [provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MoodDashboard);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    fixture?.destroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
```

---

## 5. Verification Method

### 5.1 Machine-Applicable Patch Application
To apply the entire remediation package in a single command from the project root:
```powershell
git apply c:\Users\sandi\Documents\AI\MOODZ\.agents\teamwork\explorer_m2_1\frontend_vitest_remediation.patch
```
Alternatively, copy the provided proposed replacement files from `.agents/teamwork/explorer_m2_1/`:
```powershell
Copy-Item .agents/teamwork/explorer_m2_1/proposed_new-home.spec.ts moodz-frontend/src/app/pages/new-home/new-home.spec.ts
Copy-Item .agents/teamwork/explorer_m2_1/proposed_app.spec.ts moodz-frontend/src/app/app.spec.ts
Copy-Item .agents/teamwork/explorer_m2_1/proposed_navbar.spec.ts moodz-frontend/src/app/shared/navbar/navbar.spec.ts
Copy-Item .agents/teamwork/explorer_m2_1/proposed_footer.spec.ts moodz-frontend/src/app/shared/footer/footer.spec.ts
Copy-Item .agents/teamwork/explorer_m2_1/proposed_home.spec.ts moodz-frontend/src/app/pages/home/home.spec.ts
Copy-Item .agents/teamwork/explorer_m2_1/proposed_mood-agent.spec.ts moodz-frontend/src/app/pages/mood-agent/mood-agent.spec.ts
Copy-Item .agents/teamwork/explorer_m2_1/proposed_about-us.spec.ts moodz-frontend/src/app/pages/about-us/about-us.spec.ts
Copy-Item .agents/teamwork/explorer_m2_1/proposed_mood-dashboard.spec.ts moodz-frontend/src/app/pages/mood-dashboard/mood-dashboard.spec.ts
Copy-Item .agents/teamwork/explorer_m2_1/proposed_package.json moodz-frontend/package.json
```

### 5.2 Test Execution Commands
1. **Full Suite Execution via npm test**:
   ```powershell
   cd moodz-frontend
   npm test
   ```
2. **Direct Single-Run Execution via npx**:
   ```powershell
   cd moodz-frontend
   npx ng test --watch=false
   ```
3. **Targeted Spec Execution**:
   ```powershell
   cd moodz-frontend
   npx ng test --include src/app/pages/new-home/new-home.spec.ts --watch=false
   npx ng test --include src/app/app.spec.ts --watch=false
   ```

### 5.3 Expected Pass Output & Invalidation Conditions
- **Expected Success Criteria**:
  - Zero TypeScript compilation errors (`TS2305` eliminated).
  - Vitest test runner discovers all 12 test files.
  - All test files PASS (12 passed / 14 tests passed).
  - Process exits with code `0`.
- **Invalidation Conditions**:
  - Any `TS2305: Module '"./new-home"' has no exported member 'NewHome'` error.
  - Any `NullInjectorError: No provider for Router!` error.
  - Any failure asserting `querySelector('h1')`.
  - Process hang caused by missing `--watch=false`.
