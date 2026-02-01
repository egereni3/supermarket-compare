// src/app/auth/auth.ts
import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, tap } from 'rxjs/operators';
import { Observable } from 'rxjs';

const USER_KEY = 'user';
const SEARCH_CACHE_KEY = 'searchCache';
const BASKET_KEY = 'basket';

interface LoginResponse {
  success: boolean;
  error?: string;
  user_id?: number;
  email?: string;
  message?: string;
}

interface RegisterResponse {
  success: boolean;
  error?: string;
  user_id?: number;
  message?: string;
}

@Injectable({ providedIn: 'root' })
export class Auth {
  private readonly _loggedIn = signal<boolean>(this.readIsLoggedIn());
  readonly loggedIn = this._loggedIn.asReadonly();

  constructor(private http: HttpClient) {}

  private readIsLoggedIn(): boolean {
    try {
      return !!localStorage.getItem(USER_KEY);
    } catch {
      return false;
    }
  }

  login(email: string, password: string): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>('http://localhost:8000/api/login', { email, password })
      .pipe(
        tap((resp) => {
          if (resp.success && resp.user_id && resp.email) {
            const user = {
              id: resp.user_id,
              email: resp.email,
              loggedInAt: new Date().toISOString(),
            };
            localStorage.setItem(USER_KEY, JSON.stringify(user));
            this._loggedIn.set(true);
          }
        })
      );
  }

  register(email: string, password: string): Observable<RegisterResponse> {
    return this.http
      .post<RegisterResponse>('http://localhost:8000/api/register', { email, password });
  }

  logout(): void {
    try {
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(SEARCH_CACHE_KEY);
      localStorage.removeItem(BASKET_KEY);
    } catch {}
    this._loggedIn.set(false);
  }

  isLoggedIn(): boolean {
    return this._loggedIn();
  }
 
  // Return parsed user object from localStorage (or null)
  getUser(): { id: number; email: string; loggedInAt: string } | null {
    try {
      const raw = localStorage.getItem(USER_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  // Update the locally stored email (does not update server)
  updateLocalEmail(newEmail: string): void {
    try {
      const user = this.getUser();
      if (!user) return;
      const updated = { ...user, email: newEmail };
      localStorage.setItem(USER_KEY, JSON.stringify(updated));
    } catch {}
  }
 
  // Update user on server (email and/or password)
  updateUser(userId: number, payload: { email?: string; password?: string }) {
    return this.http.put<{ success: boolean; error?: string; message?: string }>(
      `http://localhost:8000/api/user/${userId}`,
      payload
    );
  }
}