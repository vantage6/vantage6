import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthResult } from 'src/app/models/api/auth.model';
import { LoginForm } from 'src/app/models/forms/login-form.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { LoginErrorService } from 'src/app/services/login-error.service';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatButton } from '@angular/material/button';
import { NgIf } from '@angular/common';
import { AlertComponent } from '../../../components/alerts/alert/alert.component';
import { TranslateModule } from '@ngx-translate/core';

@Component({
    selector: 'app-mfa-code',
    templateUrl: './mfa-code.component.html',
    styleUrls: ['./mfa-code.component.scss'],
    imports: [
        MatCard,
        MatCardHeader,
        MatCardTitle,
        MatCardContent,
        ReactiveFormsModule,
        MatFormField,
        MatLabel,
        MatInput,
        MatButton,
        RouterLink,
        NgIf,
        AlertComponent,
        TranslateModule
    ]
})
export class MfaCodeComponent implements OnInit {
  loginForm = this.fb.nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
    mfaCode: ['', Validators.required]
  });
  routes = routePaths;

  constructor(
    public loginErrorService: LoginErrorService,
    private router: Router,
    private fb: FormBuilder,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loginErrorService.clearError();
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
