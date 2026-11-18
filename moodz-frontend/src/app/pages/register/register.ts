import { Component, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
    selector: 'app-register',
    imports: [CommonModule, FormsModule, RouterModule],
    templateUrl: './register.html',
    styleUrl: './register.css',
})
export class RegisterComponent {
    private authService = inject(AuthService);
    private router = inject(Router);

    name = signal('');
    email = signal('');
    password = signal('');
    confirmPassword = signal('');
    error = signal<string | null>(null);
    isLoading = signal(false);
    showPassword = signal(false);

    // Dynamic NIST password strength score: 0 to 4
    passwordStrength = computed(() => {
        const pw = this.password();
        if (!pw) return 0;
        if (pw.length < 10) return 1;

        let score = 1;
        if (pw.length >= 12) score++;
        if (pw.length >= 16) score++;
        if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
        if (/[0-9]/.test(pw) || /[^A-Za-z0-9]/.test(pw)) score++;
        return Math.min(score, 4);
    });

    strengthLabel = computed(() => {
        const s = this.passwordStrength();
        switch (s) {
            case 0: return '';
            case 1: return 'Weak (needs 10+ characters)';
            case 2: return 'Fair (longer phrases are safer)';
            case 3: return 'Good';
            case 4: return 'Excellent passphrase';
            default: return '';
        }
    });

    strengthColor = computed(() => {
        const s = this.passwordStrength();
        switch (s) {
            case 1: return '#ef4444';
            case 2: return '#f59e0b';
            case 3: return '#3b82f6';
            case 4: return '#10b981';
            default: return '#e5e7eb';
        }
    });

    togglePasswordVisibility(): void {
        this.showPassword.update(v => !v);
    }

    async onSubmit(): Promise<void> {
        const nameVal = this.name().trim();
        const emailVal = this.email().trim();
        const passwordVal = this.password();
        const confirmVal = this.confirmPassword();

        if (!nameVal || !emailVal || !passwordVal || !confirmVal) {
            this.error.set('Please fill in all fields');
            return;
        }

        if (passwordVal.length < 10) {
            this.error.set('Password must be at least 10 characters per NIST SP 800-63B standards');
            return;
        }

        if (passwordVal !== confirmVal) {
            this.error.set('Passwords do not match');
            return;
        }

        this.error.set(null);
        this.isLoading.set(true);

        try {
            await this.authService.register(nameVal, emailVal, passwordVal);
            this.router.navigate(['/']);
        } catch (err: any) {
            this.error.set(err.message || 'Registration failed. Please try again.');
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
