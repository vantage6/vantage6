import { Injectable } from '@angular/core';
import { LoginForm } from '../models/forms/login-form.model';
import { ApiService } from './api.service';
import { Login } from '../models/api/auth.model';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_ID } from '../models/constants/sessionStorage';
import { PermissionService } from './permission.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  constructor(
    private apiService: ApiService,
    private permissionService: PermissionService
  ) {}

  async login(loginForm: LoginForm): Promise<boolean> {
    const data = {
      username: loginForm.username,
      password: loginForm.password
    };
    const result = await this.apiService.postForApi<Login>('/token/user', data);
    this.setSession(result);
    return await this.isAuthenticated();
  }

  async isAuthenticated(): Promise<boolean> {
    const token = sessionStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) {
      return false;
    }

    const isExpired = Date.now() >= JSON.parse(atob(token.split('.')[1])).exp * 1000;
    if (!isExpired) {
      await this.permissionService.initData();
    }
    return !isExpired;
  }

  logout(): void {
    this.clearSession();
  }

  private setSession(result: Login): void {
    this.clearSession();

    if (!result.access_token) return;

    sessionStorage.setItem(ACCESS_TOKEN_KEY, result.access_token);
    sessionStorage.setItem(REFRESH_TOKEN_KEY, result.refresh_token);
    sessionStorage.setItem(USER_ID, result.user_url.split('/').pop() || '');
  }

  private clearSession(): void {
    sessionStorage.clear();
  }
}
