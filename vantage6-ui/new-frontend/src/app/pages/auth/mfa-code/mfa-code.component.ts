import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthResult } from 'src/app/models/api/auth.model';
import { LoginForm } from 'src/app/models/forms/login-form.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';

@Component({
  selector: 'app-mfa-code',
  templateUrl: './mfa-code.component.html',
  styleUrls: ['./mfa-code.component.scss']
})
export class MfaCodeComponent implements OnInit {
  loginForm = this.fb.nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
    mfaCode: ['', Validators.required]
  });
  routes = routePaths;

  constructor(
    private router: Router,
    private fb: FormBuilder,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    if (!this.authService.username || !this.authService.password) {
      this.router.navigate([routePaths.login]);
    }
    this.loginForm.controls['username'].setValue(this.authService.username);
    this.loginForm.controls['password'].setValue(this.authService.password);
  }

  async onSubmit(): Promise<void> {
    if (!this.loginForm.valid) return;

    const authStatus = await this.authService.login(this.loginForm.value as LoginForm);
    if (authStatus == AuthResult.Success) {
      this.router.navigate([routePaths.home]);
    }
  }
}
