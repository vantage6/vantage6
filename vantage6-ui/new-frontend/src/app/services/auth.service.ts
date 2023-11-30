import { Injectable } from '@angular/core';
import { LoginForm } from '../models/forms/login-form.model';
import { ApiService } from './api.service';
import { AuthResult, ChangePassword, Login, SetupMFA } from '../models/api/auth.model';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_ID } from '../models/constants/sessionStorage';
import { PermissionService } from './permission.service';
import { Router } from '@angular/router';
import { routePaths } from '../routes';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  qr_uri = '';
  otp_code = '';

  constructor(
    private apiService: ApiService,
    private permissionService: PermissionService,
    private router: Router
  ) {}

  async isAuthenticated(): Promise<AuthResult> {
    const token = sessionStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) {
      return AuthResult.Failure;
    }

    const isExpired = Date.now() >= JSON.parse(atob(token.split('.')[1])).exp * 1000;
    if (!isExpired) {
      await this.permissionService.initData();
    }
    if (!isExpired) {
      return AuthResult.Success;
    }
    return AuthResult.Failure;
  }

  // TODO instead of boolean return an interface that sets to go to setup MFA
  async login(loginForm: LoginForm): Promise<AuthResult> {
    const data = {
      username: loginForm.username,
      password: loginForm.password
    };
    const result = await this.apiService.postForApi<Login | SetupMFA>('/token/user', data);

    if ('qr_uri' in result) {
      // redirect to setup MFA
      this.qr_uri = result.qr_uri;
      this.otp_code = result.otp_secret;
      // this.router.navigate([routePaths.setupMFA]);
      return AuthResult.RedirectMFA;
    } else {
      // login success
      this.setSession(result);
      return await this.isAuthenticated();
    }
  }

  logout(): void {
    this.clearSession();
  }

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await this.apiService.patchForApi<ChangePassword>('/password/change', {
      current_password: oldPassword,
      new_password: newPassword
    });
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
