import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from 'src/app/auth/services/auth.service';
import { TokenStorageService } from 'src/app/services/common/token-storage.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { environment } from 'src/environments/environment';

let BACKGROUND_IMAGES = [
  'cuppolone.jpg',
  'taipei101.png',
  'trolltunga.jpg',
  // 'harukas2.jpg',
  'petronas.jpg',
];

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
  background_img = '';

  constructor(
    private authService: AuthService,
    private tokenStorage: TokenStorageService,
    private userPermission: UserPermissionService,
    private router: Router
  ) {}

  ngOnInit(): void {
    if (this.tokenStorage.getToken()) {
      this.isLoggedIn = true;
      this.router.navigateByUrl('/home');
    }
    this.background_img = this._pickBackgroundImage();
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

  private _pickBackgroundImage(): string {
    // pick random background image
    return BACKGROUND_IMAGES[
      Math.floor(Math.random() * BACKGROUND_IMAGES.length)
    ];
  }

  _getBackgroundImage() {
    return `url('../assets/images/login_backgrounds/${this.background_img}')`;
  }
}
