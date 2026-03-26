import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
    {
        path: 'login',
        loadComponent: () => import('./pages/login/login').then(m => m.LoginComponent)
    },
    {
        path: 'register',
        loadComponent: () => import('./pages/register/register').then(m => m.RegisterComponent)
    },
    {
        path: '',
        loadComponent: () => import('./pages/new-home/new-home').then(m => m.NewHomeComponent),
        canActivate: [authGuard]
    },
    {
        path: 'mood-agent',
        loadComponent: () => import('./pages/mood-agent/mood-agent').then(m => m.MoodAgent),
        canActivate: [authGuard]
    },
    {
        path: 'mood-history',
        loadComponent: () => import('./pages/mood-history/mood-history').then(m => m.MoodHistory),
        canActivate: [authGuard]
    },
    {
        path: 'mood-dashboard',
        loadComponent: () => import('./pages/mood-dashboard/mood-dashboard').then(m => m.MoodDashboard),
        canActivate: [authGuard]
    },
    {
        path: 'about-us',
        loadComponent: () => import('./pages/about-us/about-us').then(m => m.AboutUs),
        canActivate: [authGuard]
    }
];
