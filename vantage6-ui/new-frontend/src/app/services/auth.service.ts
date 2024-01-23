import { Injectable } from '@angular/core';
import { LoginForm, LostPasswordForm, MFAResetTokenForm, PasswordResetTokenForm } from '../models/forms/login-form.model';
import { ApiService } from './api.service';
import { AuthResult, ChangePassword, Login, LoginSubmit, LoginRecoverLost, SetupMFA, LoginRecoverSubmit } from '../models/api/auth.model';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_ID } from '../models/constants/sessionStorage';
import { PermissionService } from './permission.service';
import { TokenStorageService } from './token-storage.service';
import { SocketioConnectService } from './socketio-connect.service';
import { LoginErrorService } from './login-error.service';

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
    private permissionService: PermissionService,
    private tokenStorageService: TokenStorageService,
    private socketConnectService: SocketioConnectService,
    private loginErrorService: LoginErrorService
  ) {}

  async isAuthenticated(): Promise<AuthResult> {
    const token = this.tokenStorageService.getToken();
    if (!token) {
      return AuthResult.Failure;
    }

    const isExpired = Date.now() >= JSON.parse(atob(token.split('.')[1])).exp * 1000;
    if (!isExpired) {
      await this.permissionService.initData();
      await this.socketConnectService.connect();
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
    this.loginErrorService.clearError();
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
      this.tokenStorageService.setSession(result);
      return await this.isAuthenticated();
    }
  }

  logout(): void {
    this.tokenStorageService.clearSession();
    this.permissionService.clear();
    this.socketConnectService.disconnect();
  }

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await this.apiService.patchForApi<ChangePassword>('/password/change', {
      current_password: oldPassword,
      new_password: newPassword
    });
  }

  async passwordLost(forgotPasswordForm: LostPasswordForm): Promise<string> {
    const data: LoginRecoverSubmit = {};
    if (forgotPasswordForm.email) {
      data.email = forgotPasswordForm.email;
    }
    if (forgotPasswordForm.username) {
      data.username = forgotPasswordForm.username;
    }
    const result = await this.apiService.postForApi<LoginRecoverLost>('/recover/lost', data);
    if (result.msg) {
      return result.msg;
    }
    return '';
  }

  async passwordRecover(resetForm: PasswordResetTokenForm): Promise<boolean> {
    const data = {
      reset_token: resetForm.resetToken,
      password: resetForm.password
    };
    const result = await this.apiService.postForApi<ChangePassword>('/recover/reset', data);
    if (result.msg) {
      return true;
    }
    return false;
  }

  async MFALost(): Promise<string> {
    const data = {
      username: this.username,
      password: this.password
    };
    const result = await this.apiService.postForApi<LoginRecoverLost>('/recover/2fa/lost', data);
    if (result.msg) {
      return result.msg;
    }
    return '';
  }

  async MFARecover(resetForm: MFAResetTokenForm): Promise<boolean> {
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
}
