import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';

import { LoginComponent } from './login';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        provideRouter([]),
        provideHttpClient()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    fixture?.destroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
    expect(component.mfaRequired()).toBe(false);
  });

  it('should require email and password before submitting', async () => {
    component.email.set('');
    component.password.set('');
    await component.onSubmit();
    expect(component.error()).toBe('Please fill in all fields');
  });

  it('should toggle MFA mode and backup code input cleanly', () => {
    component.mfaRequired.set(true);
    component.mfaTicket.set('mock-ticket');
    expect(component.isBackupCode()).toBe(false);

    component.toggleBackupCodeMode();
    expect(component.isBackupCode()).toBe(true);

    component.cancelMfa();
    expect(component.mfaRequired()).toBe(false);
    expect(component.mfaTicket()).toBeNull();
  });
});
