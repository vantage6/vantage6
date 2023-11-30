import { Component } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthResult } from 'src/app/models/api/auth.model';
import { LoginForm } from 'src/app/models/forms/login-form.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  loginForm = this.fb.nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required]
  });

  constructor(
    private router: Router,
    private fb: FormBuilder,
    private authService: AuthService
  ) {}

  async onSubmit(): Promise<void> {
    if (!this.loginForm.valid) return;

    const authStatus = await this.authService.login(this.loginForm.value as LoginForm);
    if (authStatus == AuthResult.Success) {
      this.router.navigate([routePaths.home]);
    } else if (authStatus == AuthResult.RedirectMFA) {
      this.router.navigate([routePaths.setupMFA]);
    }
  }
}
