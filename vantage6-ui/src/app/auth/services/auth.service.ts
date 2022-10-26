import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';

import { SignOutService } from 'src/app/services/common/sign-out.service';
import { TokenStorageService } from 'src/app/services/common/token-storage.service';
import { environment } from 'src/environments/environment';
import { UserPermissionService } from './user-permission.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  username: string | undefined;
  password: string | undefined;
  qr_uri: string | undefined;

  constructor(
    private http: HttpClient,
    private signOutService: SignOutService,
    private userPermission: UserPermissionService,
    private tokenStorageService: TokenStorageService,
    private router: Router
  ) {}

  login(
    username: string,
    password: string,
    mfa_code: string | undefined = undefined
  ): Observable<any> {
    // ensure cached data is cleared before login
    this.signOutService.clearDataServices();

    this.username = username;
    this.password = password;
    let params: any = {
      username: username,
      password: password,
    };
    if (mfa_code !== undefined) {
      params['mfa_code'] = mfa_code;
    }
    // login
    return this.http.post<any>(environment.api_url + '/token/user', params);
  }

  clearCredentials(): void {
    this.username = undefined;
    this.password = undefined;
    this.qr_uri = undefined;
  }

  async onLogin(token: any) {
    await this.tokenStorageService.setLoginData(token);

    // set user permissions
    this.userPermission.setup();

    // after login, go to home
    this.router.navigateByUrl('/home');

    // clear credentials
    this.clearCredentials();
  }
}
