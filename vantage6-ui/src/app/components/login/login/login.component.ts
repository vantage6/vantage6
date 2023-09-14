import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from 'src/app/auth/services/auth.service';
import { TokenStorageService } from 'src/app/services/common/token-storage.service';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent implements OnInit {
  form: any = {
    username: null,
    password: null,
  };
  isLoggedIn = false;
  isLoginFailed = false;
  errorMessage = '';
  server_url: string;

  constructor(
    private authService: AuthService,
    private tokenStorage: TokenStorageService,
    private router: Router
  ) {
    this.setServerURL();
  }

  ngOnInit(): void {
    if (this.tokenStorage.getToken()) {
      this.isLoggedIn = true;
      this.router.navigateByUrl('/home');
    }
  }

  onSubmit(): void {
    const { username, password } = this.form;

    this.login(username, password);
  }

  login(username: string, password: string): void {
    this.authService.login(username, password).subscribe(
      (data) => {
        if ('qr_uri' in data) {
          // user still has to set up two factor authentication
          this.authService.qr_uri = data['qr_uri'];
          this.authService.otp_code = data['otp_secret'];
          this.router.navigateByUrl('/setup_mfa');
        } else if (!('access_token' in data)) {
          // if there is no access token, this means user has to also submit
          // an MFA code
          this.router.navigateByUrl('/mfa_code');
        } else {
          // logged in successfully!
          this._onSuccessfulLogin(data);
        }
      },
      (err) => {
        if (err.status === 0) {
          this.errorMessage = `Cannot connect to server! Server URL is ${environment.api_url}.`;
        } else if (err.error.msg) {
          this.errorMessage = err.error.msg;
        } else {
          this.errorMessage = 'An unknown error occurred!';
        }
        this.isLoginFailed = true;
        this.isLoggedIn = false;
      }
    );
  }

  private async _onSuccessfulLogin(data: any): Promise<void> {
    this.isLoginFailed = false;
    this.isLoggedIn = true;
    this.authService.onLogin(data);
  }

  reloadPage(): void {
    window.location.reload();
  }

  private setServerURL(): void {
    // find the server url. Take into account that the UI may be served from
    // the same machine as the server, but remote from the user.
    if (environment.api_url.includes('localhost') &&
        window.location.hostname !== 'localhost'){
      this.server_url = window.location.hostname + environment.api_path;
    } else {
      this.server_url = environment.api_url;
    }
  }
}
