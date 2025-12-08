import { Routes } from '@angular/router';

export const routes: Routes = [
    {
        path: '',
        loadComponent: () => import('./pages/home/home').then(m => m.Home)
    },
    {
        path: 'mood-agent',
        loadComponent: () => import('./pages/mood-agent/mood-agent').then(m => m.MoodAgent)
    }
];
