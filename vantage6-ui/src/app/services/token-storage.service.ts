import { Injectable } from '@angular/core';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USERNAME, USER_ID } from '../models/constants/sessionStorage';
import { Login, AuthResult } from '../models/api/auth.model';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class TokenStorageService {
  loggedIn$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  constructor() {}

  async isAuthenticated(): Promise<AuthResult> {
    const token = this.getToken();
    if (!token) {
      this.loggedIn$.next(false);
      return AuthResult.Failure;
    }

    const isExpired = Date.now() >= JSON.parse(atob(token.split('.')[1])).exp * 1000;
    if (!isExpired) {
      this.loggedIn$.next(true);
      return AuthResult.Success;
    }
    this.loggedIn$.next(false);
    return AuthResult.Failure;
  }

  loginObservable(): Observable<boolean> {
    return this.loggedIn$.asObservable();
  }

  getToken(): string | null {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY);
  }

  getUsername(): string | null {
    return sessionStorage.getItem(USERNAME);
  }

  setSession(result: Login, username: string): void {
    this.clearSession();

    if (!result.access_token) return;

    sessionStorage.setItem(ACCESS_TOKEN_KEY, result.access_token);
    sessionStorage.setItem(REFRESH_TOKEN_KEY, result.refresh_token);
    sessionStorage.setItem(USER_ID, result.user_url.split('/').pop() || '');
    sessionStorage.setItem(USERNAME, username);
  }

  clearSession(): void {
    sessionStorage.clear();
  }
}
