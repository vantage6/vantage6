import { Injectable, inject, effect } from '@angular/core';
import Keycloak from 'keycloak-js';
import { KEYCLOAK_EVENT_SIGNAL, KeycloakEventType, typeEventArgs, ReadyArgs } from 'keycloak-angular';
import { BehaviorSubject, Observable } from 'rxjs';

// import { LoginForm, LostPasswordForm, MFAResetTokenForm, PasswordResetTokenForm } from 'src/app/models/forms/login-form.model';
import { ApiService } from './api.service';
// import {
//   AuthResult,
//   ChangePassword,
//   Login,
//   LoginSubmit,
//   LoginRecoverLost,
//   SetupMFA,
//   LoginRecoverSubmit
// } from 'src/app/models/api/auth.model';
// import { PermissionService } from './permission.service';
import { SocketioConnectService } from './socketio-connect.service';
import { LoginErrorService } from './login-error.service';
// import { EncryptionService } from './encryption.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  username = '';
  password = '';
  qr_uri = '';
  otp_code = '';

  authenticated = false;
  authenticated$ = new BehaviorSubject<boolean>(false);
  keycloakStatus: string | undefined;
  private readonly keycloak = inject(Keycloak);
  private readonly keycloakSignal = inject(KEYCLOAK_EVENT_SIGNAL);

  constructor(
    private apiService: ApiService,
    // private permissionService: PermissionService,
    private socketConnectService: SocketioConnectService,
    private loginErrorService: LoginErrorService
    // private storePermissionService: PermissionService,
    // private encryptionService: EncryptionService
  ) {
    effect(() => {
      const keycloakEvent = this.keycloakSignal();

      this.keycloakStatus = keycloakEvent.type;

      if (keycloakEvent.type === KeycloakEventType.Ready) {
        this.authenticated = typeEventArgs<ReadyArgs>(keycloakEvent.args);
        this.authenticated$.next(this.authenticated);
      }

      if (keycloakEvent.type === KeycloakEventType.AuthLogout) {
        this.authenticated = false;
        this.authenticated$.next(this.authenticated);
      }
    });
  }

  // TODO connect socket
  // async isAuthenticated(): Promise<AuthResult> {
  //   if (authResult === AuthResult.Success) {
  //     this.socketConnectService.connect();
  //   }
  //   return authResult;
  // }

  authenticatedObservable(): Observable<boolean> {
    return this.authenticated$.asObservable();
  }

  async loginWithKeycloak(): Promise<void> {
    this.keycloak.login();
  }

  async logoutWithKeycloak(): Promise<void> {
    this.keycloak.logout();
  }

  // async login(loginForm: LoginForm): Promise<AuthResult> {
  //   this.username = loginForm.username;
  //   this.password = loginForm.password;
  //   const data: LoginSubmit = {
  //     username: this.username,
  //     password: this.password
  //   };
  //   if (loginForm.mfaCode) {
  //     data.mfa_code = loginForm.mfaCode;
  //   }
  //   const result = await this.apiService.postForApi<Login | SetupMFA>('/token/user', data);
  //   this.loginErrorService.clearError();
  //   if ('qr_uri' in result) {
  //     // redirect to setup MFA
  //     this.qr_uri = result.qr_uri;
  //     this.otp_code = result.otp_secret;
  //     return AuthResult.SetupMFA;
  //   } else if (!('access_token' in result)) {
  //     // ask for MFA code
  //     return AuthResult.MFACode;
  //   } else {
  //     // login success
  //     return AuthResult.Success;
  //   }
  // }

  logout(): void {
    // this.permissionService.clear();
    // this.storePermissionService.clear();
    this.socketConnectService.disconnect();
    // this.encryptionService.clear();
    this.keycloak.logout();
  }

  // async changePassword(oldPassword: string, newPassword: string): Promise<void> {
  //   await this.apiService.patchForApi<ChangePassword>('/password/change', {
  //     current_password: oldPassword,
  //     new_password: newPassword
  //   });
  // }

  // async passwordLost(forgotPasswordForm: LostPasswordForm): Promise<string> {
  //   const data: LoginRecoverSubmit = {
  //     email: forgotPasswordForm.email
  //   };
  //   const result = await this.apiService.postForApi<LoginRecoverLost>('/recover/lost', data);
  //   if (result.msg) {
  //     return result.msg;
  //   }
  //   return '';
  // }

  // async passwordRecover(resetForm: PasswordResetTokenForm): Promise<boolean> {
  //   const data = {
  //     reset_token: resetForm.resetToken,
  //     password: resetForm.password
  //   };
  //   const result = await this.apiService.postForApi<ChangePassword>('/recover/reset', data);
  //   if (result.msg) {
  //     return true;
  //   }
  //   return false;
  // }

  // async MFALost(): Promise<string> {
  //   const data = {
  //     username: this.username,
  //     password: this.password
  //   };
  //   const result = await this.apiService.postForApi<LoginRecoverLost>('/recover/2fa/lost', data);
  //   if (result.msg) {
  //     return result.msg;
  //   }
  //   return '';
  // }

  // async MFARecover(resetForm: MFAResetTokenForm): Promise<boolean> {
  //   const data = {
  //     reset_token: resetForm.resetToken
  //   };
  //   const result = await this.apiService.postForApi<SetupMFA>('/recover/2fa/reset', data);
  //   if ('qr_uri' in result) {
  //     this.qr_uri = result.qr_uri;
  //     this.otp_code = result.otp_secret;
  //     return true;
  //   }
  //   return false;
  // }
}
