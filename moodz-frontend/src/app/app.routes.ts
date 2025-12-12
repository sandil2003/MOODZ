import { Routes } from '@angular/router';

export const routes: Routes = [
    {
        path: '',
        loadComponent: () => import('./pages/home/home').then(m => m.Home)
    },
    {
        path: 'mood-agent',
        loadComponent: () => import('./pages/mood-agent/mood-agent').then(m => m.MoodAgent)
    },
    {
        path: 'mood-history',
        loadComponent: () => import('./pages/mood-history/mood-history').then(m => m.MoodHistory)
    },
    {
        path: 'mood-dashboard',
        loadComponent: () => import('./pages/mood-dashboard/mood-dashboard').then(m => m.MoodDashboard)
    }
];
