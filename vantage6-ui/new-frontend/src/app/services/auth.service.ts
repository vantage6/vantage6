import { Injectable } from '@angular/core';
import { LoginForm, ResetTokenForm } from '../models/forms/login-form.model';
import { ApiService } from './api.service';
import { AuthResult, ChangePassword, Login, LoginSubmit, MFARecoverLost, SetupMFA } from '../models/api/auth.model';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_ID } from '../models/constants/sessionStorage';
import { PermissionService } from './permission.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  username = '';
  password = '';
  qr_uri = '';
  otp_code = '';

  constructor(
    private apiService: ApiService,
    private permissionService: PermissionService
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

  async login(loginForm: LoginForm): Promise<AuthResult> {
    this.username = loginForm.username;
    this.password = loginForm.password;
    const data: LoginSubmit = {
      username: this.username,
      password: this.password
    };
    if (loginForm.mfaCode) {
      data.mfa_code = loginForm.mfaCode;
    }
    const result = await this.apiService.postForApi<Login | SetupMFA>('/token/user', data);
    if ('qr_uri' in result) {
      // redirect to setup MFA
      this.qr_uri = result.qr_uri;
      this.otp_code = result.otp_secret;
      return AuthResult.SetupMFA;
    } else if (!('access_token' in result)) {
      // ask for MFA code
      return AuthResult.MFACode;
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

  async MFALost(): Promise<string> {
    const data = {
      username: this.username,
      password: this.password
    };
    const result = await this.apiService.postForApi<MFARecoverLost>('/recover/2fa/lost', data);
    if (result.msg) {
      return result.msg;
    }
    return '';
  }

  async MFARecover(resetForm: ResetTokenForm): Promise<boolean> {
    const data = {
      reset_token: resetForm.resetToken
    };
    const result = await this.apiService.postForApi<SetupMFA>('/recover/2fa/reset', data);
    if ('qr_uri' in result) {
      this.qr_uri = result.qr_uri;
      this.otp_code = result.otp_secret;
      return true;
    }
    return false;
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
