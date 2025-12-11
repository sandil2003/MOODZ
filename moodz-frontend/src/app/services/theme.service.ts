import { Injectable, signal, effect } from '@angular/core';

@Injectable({
    providedIn: 'root'
})
export class ThemeService {
    darkMode = signal<boolean>(false);

    constructor() {
        console.log('ThemeService initialized');

        // Load theme preference from localStorage
        const savedTheme = localStorage.getItem('darkMode');
        console.log('Saved theme from localStorage:', savedTheme);

        if (savedTheme !== null) {
            this.darkMode.set(savedTheme === 'true');
        }

        // Apply theme class to body whenever darkMode changes
        effect(() => {
            const isDark = this.darkMode();
            console.log('Dark mode changed to:', isDark);

            if (isDark) {
                document.body.classList.add('dark-mode');
                console.log('Added dark-mode class to body');
            } else {
                document.body.classList.remove('dark-mode');
                console.log('Removed dark-mode class from body');
            }
        });
    }

    toggleDarkMode(): void {
        const newValue = !this.darkMode();
        console.log('Toggling dark mode to:', newValue);
        this.darkMode.set(newValue);
        localStorage.setItem('darkMode', String(newValue));
        console.log('Saved to localStorage:', newValue);
    }
}
