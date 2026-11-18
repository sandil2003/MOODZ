import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';

import { RegisterComponent } from './register';

describe('RegisterComponent', () => {
  let component: RegisterComponent;
  let fixture: ComponentFixture<RegisterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RegisterComponent],
      providers: [
        provideRouter([]),
        provideHttpClient()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(RegisterComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    fixture?.destroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should compute password strength dynamically based on NIST guidelines', () => {
    component.password.set('');
    expect(component.passwordStrength()).toBe(0);

    // Short password (< 10 chars)
    component.password.set('short12');
    expect(component.passwordStrength()).toBe(1);

    // 12+ character mixed passphrase
    component.password.set('correct horse battery staple 2026');
    expect(component.passwordStrength()).toBeGreaterThanOrEqual(3);
  });

  it('should reject passwords under 10 characters', async () => {
    component.name.set('Jane Doe');
    component.email.set('jane@moodz.ai');
    component.password.set('short12');
    component.confirmPassword.set('short12');
    await component.onSubmit();
    expect(component.error()).toContain('at least 10 characters');
  });

  it('should reject mismatched passwords', async () => {
    component.name.set('Jane Doe');
    component.email.set('jane@moodz.ai');
    component.password.set('longpassword1234');
    component.confirmPassword.set('mismatchedpassword1234');
    await component.onSubmit();
    expect(component.error()).toBe('Passwords do not match');
  });
});
