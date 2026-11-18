import { Injectable, signal, inject } from '@angular/core';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AuthUser {
    id: string;
    name: string;
    email: string;
    role: string;
    mfa_enabled?: boolean;
}

export interface AuthResponse {
    access_token?: string;
    token_type?: string;
    user?: AuthUser;
    mfa_required?: boolean;
    mfa_ticket?: string;
    message?: string;
}

export interface MfaSetupData {
    secret: string;
    provisioning_uri: string;
    qr_code_data_uri: string;
}

export interface MfaActivateResult {
    message: string;
    mfa_enabled: boolean;
    backup_codes: string[];
}

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private readonly API_BASE_URL = 'http://localhost:8000';
    private readonly USER_KEY = 'moodz_user_profile';
    private http = inject(HttpClient);
    private router = inject(Router);

    currentUser = signal<AuthUser | null>(this.getStoredUser());
    isAuthenticated = signal<boolean>(!!this.getStoredUser());

    constructor() {
        // Asynchronously re-validate session identity with backend cookies on app boot
        if (this.isAuthenticated()) {
            this.checkSession().catch(() => {
                this.clearLocalSession();
            });
        }
    }

    /**
     * Register a new user with NIST SP 800-63B validation and Argon2id hashing
     */
    async register(name: string, email: string, password: string): Promise<AuthResponse> {
        const response = await fetch(`${this.API_BASE_URL}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include', // Receive HttpOnly cookies
            body: JSON.stringify({ name, email, password }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
        }

        const data: AuthResponse = await response.json();
        if (data.user) {
            this.setSessionUser(data.user);
        }
        return data;
    }

    /**
     * Authenticate user with password (returns either user profile or MFA challenge)
     */
    async login(email: string, password: string): Promise<AuthResponse> {
        const response = await fetch(`${this.API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include', // Receive HttpOnly cookies
            body: JSON.stringify({ email, password }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data: AuthResponse = await response.json();

        // If MFA required, user must complete step 2
        if (data.mfa_required) {
            return data;
        }

        if (data.user) {
            this.setSessionUser(data.user);
        }
        return data;
    }

    /**
     * Complete login via 6-digit TOTP code or single-use backup code
     */
    async verifyMfa(mfa_ticket: string, code: string): Promise<AuthResponse> {
        const response = await fetch(`${this.API_BASE_URL}/api/auth/mfa/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include', // Receive HttpOnly cookies
            body: JSON.stringify({ mfa_ticket, code }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'MFA verification failed');
        }

        const data: AuthResponse = await response.json();
        if (data.user) {
            this.setSessionUser(data.user);
        }
        return data;
    }

    /**
     * Rotate refresh token using HttpOnly cookie (used by HTTP interceptor)
     */
    refreshToken(): Observable<any> {
        return this.http.post(
            `${this.API_BASE_URL}/api/auth/refresh`,
            {},
            { withCredentials: true }
        );
    }

    /**
     * Check current session validity via /api/auth/me
     */
    async checkSession(): Promise<AuthUser> {
        const response = await fetch(`${this.API_BASE_URL}/api/auth/me`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
        });

        if (!response.ok) {
            throw new Error('Session invalid');
        }

        const user: AuthUser = await response.json();
        this.setSessionUser(user);
        return user;
    }

    /**
     * Setup TOTP MFA: returns base32 secret and QR code URI
     */
    async setupMfa(): Promise<MfaSetupData> {
        const response = await fetch(`${this.API_BASE_URL}/api/auth/mfa/setup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to setup MFA');
        }
        return response.json();
    }

    /**
     * Confirm initial TOTP code to activate MFA
     */
    async activateMfa(secret: string, code: string): Promise<MfaActivateResult> {
        const response = await fetch(`${this.API_BASE_URL}/api/auth/mfa/activate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ secret, code }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to activate MFA');
        }

        const result: MfaActivateResult = await response.json();
        if (this.currentUser()) {
            this.currentUser.update(u => u ? { ...u, mfa_enabled: true } : null);
        }
        return result;
    }

    /**
     * Disable MFA on account
     */
    async disableMfa(): Promise<void> {
        const response = await fetch(`${this.API_BASE_URL}/api/auth/mfa/disable`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to disable MFA');
        }

        if (this.currentUser()) {
            this.currentUser.update(u => u ? { ...u, mfa_enabled: false } : null);
        }
    }

    /**
     * Logout: revoke session on server, clear HttpOnly cookies, clear client signals
     */
    async logout(): Promise<void> {
        try {
            await fetch(`${this.API_BASE_URL}/api/auth/logout`, {
                method: 'POST',
                credentials: 'include',
            });
        } catch {
            // Ignore network errors on logout
        } finally {
            this.clearLocalSession();
            this.router.navigate(['/login']);
        }
    }

    /**
     * Terminate all active sessions across all devices
     */
    async logoutAll(): Promise<void> {
        try {
            await fetch(`${this.API_BASE_URL}/api/auth/logout-all`, {
                method: 'POST',
                credentials: 'include',
            });
        } finally {
            this.clearLocalSession();
            this.router.navigate(['/login']);
        }
    }

    // --- Private helpers ---

    private setSessionUser(user: AuthUser): void {
        sessionStorage.setItem(this.USER_KEY, JSON.stringify(user));
        this.currentUser.set(user);
        this.isAuthenticated.set(true);
    }

    private clearLocalSession(): void {
        sessionStorage.removeItem(this.USER_KEY);
        // Also purge any legacy localStorage tokens for backward safety
        localStorage.removeItem('moodz_token');
        localStorage.removeItem('moodz_user');
        this.currentUser.set(null);
        this.isAuthenticated.set(false);
    }

    private getStoredUser(): AuthUser | null {
        const userJson = sessionStorage.getItem(this.USER_KEY) || localStorage.getItem('moodz_user');
        if (!userJson) return null;
        try {
            return JSON.parse(userJson);
        } catch {
            return null;
        }
    }
}
