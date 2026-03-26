import { Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';

export interface AuthUser {
    id: string;
    name: string;
    email: string;
    role: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user: AuthUser;
}

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private readonly API_BASE_URL = 'http://localhost:8000';
    private readonly TOKEN_KEY = 'moodz_token';
    private readonly USER_KEY = 'moodz_user';

    currentUser = signal<AuthUser | null>(this.getStoredUser());
    isAuthenticated = signal<boolean>(this.hasToken());

    constructor(private router: Router) {}

    /**
     * Register a new user
     */
    async register(name: string, email: string, password: string): Promise<AuthResponse> {
        const response = await fetch(`${this.API_BASE_URL}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
        }

        const data: AuthResponse = await response.json();
        this.storeAuth(data);
        return data;
    }

    /**
     * Login with email and password
     */
    async login(email: string, password: string): Promise<AuthResponse> {
        const response = await fetch(`${this.API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data: AuthResponse = await response.json();
        this.storeAuth(data);
        return data;
    }

    /**
     * Logout — clear tokens and redirect
     */
    logout(): void {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
        this.currentUser.set(null);
        this.isAuthenticated.set(false);
        this.router.navigate(['/login']);
    }

    /**
     * Get the stored JWT token
     */
    getToken(): string | null {
        return localStorage.getItem(this.TOKEN_KEY);
    }

    // --- Private helpers ---

    private storeAuth(data: AuthResponse): void {
        localStorage.setItem(this.TOKEN_KEY, data.access_token);
        localStorage.setItem(this.USER_KEY, JSON.stringify(data.user));
        this.currentUser.set(data.user);
        this.isAuthenticated.set(true);
    }

    private hasToken(): boolean {
        return !!localStorage.getItem(this.TOKEN_KEY);
    }

    private getStoredUser(): AuthUser | null {
        const userJson = localStorage.getItem(this.USER_KEY);
        if (!userJson) return null;
        try {
            return JSON.parse(userJson);
        } catch {
            return null;
        }
    }
}
