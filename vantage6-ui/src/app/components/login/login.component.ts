import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from 'src/app/auth/services/auth.service';
import { TokenStorageService } from 'src/app/services/common/token-storage.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { environment } from 'src/environments/environment';

let BACKGROUND_IMAGES = ['cuppolone.jpg', 'taipei101.png', 'trolltunga.jpg'];

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

  // TODO count number of times login failed?
  // TODO if user is logged in, force that it redirects to HomeComponent

  constructor(
    private authService: AuthService,
    private tokenStorage: TokenStorageService,
    private userPermission: UserPermissionService,
    private router: Router
  ) {}

  ngOnInit(): void {
    if (this.tokenStorage.getToken()) {
      this.isLoggedIn = true;
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
        // on successfull login
        this._onSuccessfulLogin(data);

        // after login, go to home
        this.router.navigateByUrl('/home');
      },
      (err) => {
        if (err.status === 0) {
          this.errorMessage = `Cannot connect to server! Server URL is ${environment.api_url}.`;
        } else {
          this.errorMessage = err.error.msg;
        }
        this.isLoginFailed = true;
        this.isLoggedIn = false;
      }
    );
  }

  private async _onSuccessfulLogin(data: any): Promise<void> {
    // TODO ensure await is functional
    await this.tokenStorage.setLoginData(data);

    this.isLoginFailed = false;
    this.isLoggedIn = true;

    // set user permissions
    this.userPermission.setup();
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
