import { Injectable } from '@angular/core';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_ID } from '../models/constants/sessionStorage';
import { Login } from '../models/api/auth.model';

@Injectable({
  providedIn: 'root'
})
export class TokenStorageService {
  constructor() {}

  getToken(): string | null {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY);
  }

  setSession(result: Login): void {
    this.clearSession();

    if (!result.access_token) return;

    sessionStorage.setItem(ACCESS_TOKEN_KEY, result.access_token);
    sessionStorage.setItem(REFRESH_TOKEN_KEY, result.refresh_token);
    sessionStorage.setItem(USER_ID, result.user_url.split('/').pop() || '');
  }

  clearSession(): void {
    sessionStorage.clear();
  }
}
