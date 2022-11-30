import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from 'src/app/auth/services/auth.service';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-mfa-code',
  templateUrl: './mfa-code.component.html',
  styleUrls: ['./mfa-code.component.scss'],
})
export class MfaCodeComponent implements OnInit {
  form: any = {
    mfa_code: null,
  };
  isLoginFailed = false;
  errorMessage = '';

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit(): void {
    if (
      this.authService.username === undefined ||
      this.authService.password === undefined
    ) {
      this.router.navigateByUrl('/login');
    }
  }

  onSubmit(): void {
    const { mfa_code } = this.form;

    this.login(
      this.authService.username as string,
      this.authService.password as string,
      mfa_code
    );
  }

  login(username: string, password: string, mfa_code: string): void {
    this.authService.login(username, password, mfa_code).subscribe(
      (data) => {
        this.authService.onLogin(data);
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
      }
    );
  }
}
