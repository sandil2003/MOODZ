import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { vi } from 'vitest';

import { SecuritySettingsComponent } from './security-settings';
import { AuthService, AuthUser } from '../../services/auth.service';

describe('SecuritySettingsComponent', () => {
  let component: SecuritySettingsComponent;
  let fixture: ComponentFixture<SecuritySettingsComponent>;
  let mockAuthService: {
    currentUser: ReturnType<typeof signal<AuthUser | null>>;
    setupMfa: ReturnType<typeof vi.fn>;
    activateMfa: ReturnType<typeof vi.fn>;
    disableMfa: ReturnType<typeof vi.fn>;
    getActiveSessions: ReturnType<typeof vi.fn>;
    logoutAll: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    const userSignal = signal<AuthUser | null>({
      id: 'user-1',
      name: 'Sandil Perera',
      email: 'sandil@moodz.ai',
      role: 'user',
      mfa_enabled: false
    });

    mockAuthService = {
      currentUser: userSignal,
      setupMfa: vi.fn().mockResolvedValue({
        secret: 'JBSWY3DPEHPK3PXP',
        provisioning_uri: 'otpauth://totp/MOODZ:sandil@moodz.ai?secret=JBSWY3DPEHPK3PXP',
        qr_code_data_uri: 'data:image/png;base64,iVBORw0KGgo='
      }),
      activateMfa: vi.fn().mockImplementation(async () => {
        userSignal.update(u => u ? { ...u, mfa_enabled: true } : null);
        return {
          message: 'MFA has been successfully activated on your account.',
          mfa_enabled: true,
          backup_codes: ['AAAA-BBBB', 'CCCC-DDDD']
        };
      }),
      disableMfa: vi.fn().mockImplementation(async () => {
        userSignal.update(u => u ? { ...u, mfa_enabled: false } : null);
      }),
      getActiveSessions: vi.fn().mockResolvedValue([
        {
          id: 'sess-1',
          ip_address: '127.0.0.1',
          user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
          is_current: true,
          created_at: '2026-11-18T16:00:00',
          expires_at: '2026-11-25T16:00:00'
        }
      ]),
      logoutAll: vi.fn().mockResolvedValue(undefined)
    };

    await TestBed.configureTestingModule({
      imports: [SecuritySettingsComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: mockAuthService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SecuritySettingsComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    fixture?.destroy();
  });

  it('should create and load active sessions', () => {
    expect(component).toBeTruthy();
    expect(mockAuthService.getActiveSessions).toHaveBeenCalled();
    expect(component.sessions().length).toBe(1);
    expect(component.sessions()[0].is_current).toBe(true);
  });

  it('should start 2FA setup and populate QR code secret', async () => {
    await component.startMfaSetup();
    expect(mockAuthService.setupMfa).toHaveBeenCalled();
    expect(component.setupData()?.secret).toBe('JBSWY3DPEHPK3PXP');
  });

  it('should reject non-6-digit code before calling activateMfa', async () => {
    await component.startMfaSetup();
    component.verificationCode.set('123');
    await component.confirmMfaActivation();

    expect(mockAuthService.activateMfa).not.toHaveBeenCalled();
    expect(component.error()).toContain('6-digit numeric code');
  });

  it('should activate 2FA and display backup recovery codes', async () => {
    await component.startMfaSetup();
    component.verificationCode.set('123456');
    await component.confirmMfaActivation();

    expect(mockAuthService.activateMfa).toHaveBeenCalledWith('JBSWY3DPEHPK3PXP', '123456');
    expect(component.currentUser()?.mfa_enabled).toBe(true);
    expect(component.backupCodes()).toEqual(['AAAA-BBBB', 'CCCC-DDDD']);
    expect(component.setupData()).toBeNull();
  });

  it('should disable 2FA after confirmation', async () => {
    mockAuthService.currentUser.set({
      id: 'user-1',
      name: 'Sandil Perera',
      email: 'sandil@moodz.ai',
      role: 'user',
      mfa_enabled: true
    });

    component.requestDisableMfa();
    expect(component.confirmDisable()).toBe(true);

    await component.confirmDisableMfa();
    expect(mockAuthService.disableMfa).toHaveBeenCalled();
    expect(component.currentUser()?.mfa_enabled).toBe(false);
    expect(component.confirmDisable()).toBe(false);
  });
});
