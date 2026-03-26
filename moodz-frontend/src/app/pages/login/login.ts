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

    togglePasswordVisibility(): void {
        this.showPassword.update(v => !v);
    }

    async onSubmit(): Promise<void> {
        const emailVal = this.email().trim();
        const passwordVal = this.password();

        if (!emailVal || !passwordVal) {
            this.error.set('Please fill in all fields');
            return;
        }

        this.error.set(null);
        this.isLoading.set(true);

        try {
            await this.authService.login(emailVal, passwordVal);
            this.router.navigate(['/']);
        } catch (err: any) {
            this.error.set(err.message || 'Login failed. Please try again.');
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
