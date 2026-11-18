import { HttpInterceptorFn, HttpErrorResponse, HttpRequest, HttpHandlerFn, HttpEvent } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { catchError, filter, switchMap, take, throwError, BehaviorSubject, Observable } from 'rxjs';

// Synchronization variables for handling concurrent 401s
let isRefreshing = false;
const refreshTokenSubject = new BehaviorSubject<boolean | null>(null);

export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  const authService = inject(AuthService);

  // 1. Always attach credentials (HttpOnly cookies) to every backend request
  const authReq = req.clone({
    withCredentials: true
  });

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // 2. Intercept 401 Unauthorized errors (excluding auth handshake endpoints)
      if (
        error.status === 401 &&
        !req.url.includes('/api/auth/login') &&
        !req.url.includes('/api/auth/refresh') &&
        !req.url.includes('/api/auth/mfa/verify')
      ) {
        return handle401Error(authReq, next, authService);
      }

      return throwError(() => error);
    })
  );
};

function handle401Error(
  request: HttpRequest<unknown>,
  next: HttpHandlerFn,
  authService: AuthService
): Observable<HttpEvent<unknown>> {
  if (!isRefreshing) {
    isRefreshing = true;
    refreshTokenSubject.next(null);

    return authService.refreshToken().pipe(
      switchMap(() => {
        isRefreshing = false;
        refreshTokenSubject.next(true);
        // Retry original request with new session cookie
        return next(request);
      }),
      catchError((err) => {
        isRefreshing = false;
        refreshTokenSubject.next(false);
        authService.logout();
        return throwError(() => err);
      })
    );
  } else {
    // Queue subsequent requests until token refresh completes
    return refreshTokenSubject.pipe(
      filter((result): result is boolean => result !== null),
      take(1),
      switchMap((success) => {
        if (success) {
          return next(request);
        } else {
          return throwError(() => new Error('Session expired'));
        }
      })
    );
  }
}
