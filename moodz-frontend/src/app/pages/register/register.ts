import { Component, signal, inject } from '@angular/core';
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

        if (passwordVal.length < 8) {
            this.error.set('Password must be at least 8 characters');
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
