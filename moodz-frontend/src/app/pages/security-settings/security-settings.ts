import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService, MfaSetupData, SessionInfo } from '../../services/auth.service';

@Component({
    selector: 'app-security-settings',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterLink],
    templateUrl: './security-settings.html',
    styleUrl: './security-settings.css'
})
export class SecuritySettingsComponent implements OnInit {
    private authService = inject(AuthService);

    currentUser = this.authService.currentUser;

    // 2FA Setup state
    setupData = signal<MfaSetupData | null>(null);
    verificationCode = signal('');
    backupCodes = signal<string[] | null>(null);
    isSettingUp = signal(false);
    isActivating = signal(false);
    isDisabling = signal(false);
    confirmDisable = signal(false);
    showManualSecret = signal(false);
    copiedSecret = signal(false);
    copiedBackupCodes = signal(false);

    // Feedback state
    error = signal<string | null>(null);
    successMessage = signal<string | null>(null);

    // Active sessions state
    sessions = signal<SessionInfo[]>([]);
    loadingSessions = signal(false);
    confirmLogoutAll = signal(false);
    isLoggingOutAll = signal(false);

    ngOnInit(): void {
        this.loadSessions();
    }

    async loadSessions(): Promise<void> {
        this.loadingSessions.set(true);
        try {
            const list = await this.authService.getActiveSessions();
            this.sessions.set(list);
        } catch {
            // Silently handle if offline or session check fails
        } finally {
            this.loadingSessions.set(false);
        }
    }

    async startMfaSetup(): Promise<void> {
        this.error.set(null);
        this.successMessage.set(null);
        this.backupCodes.set(null);
        this.isSettingUp.set(true);

        try {
            const data = await this.authService.setupMfa();
            this.setupData.set(data);
            this.verificationCode.set('');
        } catch (err: any) {
            this.error.set(err.message || 'Unable to start 2FA setup. Please try again.');
        } finally {
            this.isSettingUp.set(false);
        }
    }

    cancelMfaSetup(): void {
        this.setupData.set(null);
        this.verificationCode.set('');
        this.showManualSecret.set(false);
        this.error.set(null);
    }

    async confirmMfaActivation(): Promise<void> {
        const setup = this.setupData();
        const code = this.verificationCode().replace(/\s+/g, '').trim();

        if (!setup) return;
        if (!/^\d{6}$/.test(code)) {
            this.error.set('Please enter the 6-digit numeric code from your authenticator app.');
            return;
        }

        this.error.set(null);
        this.isActivating.set(true);

        try {
            const result = await this.authService.activateMfa(setup.secret, code);
            this.setupData.set(null);
            this.verificationCode.set('');
            this.backupCodes.set(result.backup_codes);
            this.successMessage.set(result.message || 'Two-factor authentication is now enabled!');
        } catch (err: any) {
            this.error.set(err.message || 'Invalid verification code. Please check your device clock and try again.');
        } finally {
            this.isActivating.set(false);
        }
    }

    dismissBackupCodes(): void {
        this.backupCodes.set(null);
    }

    async copySecret(): Promise<void> {
        const secret = this.setupData()?.secret;
        if (!secret) return;
        try {
            await navigator.clipboard.writeText(secret);
            this.copiedSecret.set(true);
            setTimeout(() => this.copiedSecret.set(false), 2000);
        } catch {
            // Clipboard API fallback ignored
        }
    }

    async copyAllBackupCodes(): Promise<void> {
        const codes = this.backupCodes();
        if (!codes || codes.length === 0) return;
        const text = `MOODZ 2FA Recovery Backup Codes\nKeep these safe — each code can only be used once:\n\n${codes.join('\n')}`;
        try {
            await navigator.clipboard.writeText(text);
            this.copiedBackupCodes.set(true);
            setTimeout(() => this.copiedBackupCodes.set(false), 2500);
        } catch {
            // Clipboard API fallback ignored
        }
    }

    downloadBackupCodes(): void {
        const codes = this.backupCodes();
        if (!codes || codes.length === 0) return;
        const content = [
            'MOODZ Mental Wellness - 2FA Recovery Codes',
            `Account: ${this.currentUser()?.email || 'User'}`,
            `Generated: ${new Date().toISOString()}`,
            '',
            'Each backup code can only be used ONCE to access your account if you lose your authenticator device.',
            'Store these in a password manager or secure offline location:',
            '',
            ...codes,
            ''
        ].join('\n');

        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'moodz-2fa-backup-codes.txt';
        link.click();
        URL.revokeObjectURL(url);
    }

    requestDisableMfa(): void {
        this.confirmDisable.set(true);
        this.error.set(null);
        this.successMessage.set(null);
    }

    cancelDisableMfa(): void {
        this.confirmDisable.set(false);
    }

    async confirmDisableMfa(): Promise<void> {
        this.error.set(null);
        this.isDisabling.set(true);

        try {
            await this.authService.disableMfa();
            this.confirmDisable.set(false);
            this.backupCodes.set(null);
            this.successMessage.set('Two-factor authentication has been disabled.');
        } catch (err: any) {
            this.error.set(err.message || 'Failed to disable 2FA. Please try again.');
        } finally {
            this.isDisabling.set(false);
        }
    }

    async logoutAllDevices(): Promise<void> {
        this.isLoggingOutAll.set(true);
        try {
            await this.authService.logoutAll();
        } finally {
            this.isLoggingOutAll.set(false);
        }
    }

    formatUserAgent(ua?: string): string {
        if (!ua || ua === 'unknown') return 'Unknown Device';
        let browser = 'Browser';
        let os = 'Device';

        if (ua.includes('Edg/')) browser = 'Microsoft Edge';
        else if (ua.includes('Chrome/') && !ua.includes('Chromium/')) browser = 'Google Chrome';
        else if (ua.includes('Firefox/')) browser = 'Mozilla Firefox';
        else if (ua.includes('Safari/') && !ua.includes('Chrome/')) browser = 'Apple Safari';

        if (ua.includes('Windows')) os = 'Windows';
        else if (ua.includes('Macintosh') || ua.includes('Mac OS')) os = 'macOS';
        else if (ua.includes('iPhone') || ua.includes('iPad')) os = 'iOS';
        else if (ua.includes('Android')) os = 'Android';
        else if (ua.includes('Linux')) os = 'Linux';

        return `${browser} on ${os}`;
    }

    formatDate(isoString?: string): string {
        if (!isoString) return '';
        const date = new Date(isoString.endsWith('Z') ? isoString : `${isoString}Z`);
        if (isNaN(date.getTime())) return isoString;
        return date.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}
