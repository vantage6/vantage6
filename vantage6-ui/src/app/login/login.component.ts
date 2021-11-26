import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from '../services/auth.service';
import { TokenStorageService } from '../services/token-storage.service';
import { UserPermissionService } from '../services/user-permission.service';

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
        this.errorMessage = err.error.msg;
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
}
