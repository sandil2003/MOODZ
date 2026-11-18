import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
    selector: 'app-login',
    imports: [CommonModule, FormsModule, RouterModule],
    templateUrl: './login.html',
    styleUrl: './login.css',
})
export class LoginComponent {
    private authService = inject(AuthService);
    private router = inject(Router);

    email = signal('');
    password = signal('');
    error = signal<string | null>(null);
    isLoading = signal(false);
    showPassword = signal(false);

    // Two-step MFA State
    mfaRequired = signal(false);
    mfaTicket = signal<string | null>(null);
    mfaCode = signal('');
    isBackupCode = signal(false);

    togglePasswordVisibility(): void {
        this.showPassword.update(v => !v);
    }

    toggleBackupCodeMode(): void {
        this.isBackupCode.update(v => !v);
        this.mfaCode.set('');
        this.error.set(null);
    }

    cancelMfa(): void {
        this.mfaRequired.set(false);
        this.mfaTicket.set(null);
        this.mfaCode.set('');
        this.isBackupCode.set(false);
        this.error.set(null);
    }

    async onSubmit(): Promise<void> {
        if (this.mfaRequired()) {
            await this.onVerifyMfa();
            return;
        }

        const emailVal = this.email().trim();
        const passwordVal = this.password();

        if (!emailVal || !passwordVal) {
            this.error.set('Please fill in all fields');
            return;
        }

        this.error.set(null);
        this.isLoading.set(true);

        try {
            const res = await this.authService.login(emailVal, passwordVal);
            if (res.mfa_required && res.mfa_ticket) {
                this.mfaRequired.set(true);
                this.mfaTicket.set(res.mfa_ticket);
            } else {
                this.router.navigate(['/']);
            }
        } catch (err: any) {
            this.error.set(err.message || 'Login failed. Please try again.');
        } finally {
            this.isLoading.set(false);
        }
    }

    async onVerifyMfa(): Promise<void> {
        const codeVal = this.mfaCode().trim();
        const ticket = this.mfaTicket();

        if (!codeVal) {
            this.error.set(this.isBackupCode() ? 'Please enter a backup recovery code' : 'Please enter the 6-digit verification code');
            return;
        }

        if (!ticket) {
            this.error.set('MFA session expired. Please sign in again.');
            this.cancelMfa();
            return;
        }

        this.error.set(null);
        this.isLoading.set(true);

        try {
            await this.authService.verifyMfa(ticket, codeVal);
            this.router.navigate(['/']);
        } catch (err: any) {
            this.error.set(err.message || 'Invalid verification code. Please try again.');
        } finally {
            this.isLoading.set(false);
        }
    }

    onKeyPress(event: KeyboardEvent): void {
        if (event.key === 'Enter') {
            this.onSubmit();
        }
    }
}
