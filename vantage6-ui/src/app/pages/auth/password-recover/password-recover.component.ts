import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PasswordResetTokenForm } from 'src/app/models/forms/login-form.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { LoginErrorService } from 'src/app/services/login-error.service';
import { createCompareValidator } from 'src/app/validators/compare.validator';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { MatFormField, MatLabel, MatError } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { NgIf } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { AlertComponent } from '../../../components/alerts/alert/alert.component';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-password-recover',
  templateUrl: './password-recover.component.html',
  styleUrls: ['./password-recover.component.scss'],
  standalone: true,
  imports: [
    MatCard,
    MatCardHeader,
    MatCardTitle,
    MatCardContent,
    ReactiveFormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    NgIf,
    MatError,
    MatButton,
    AlertComponent,
    TranslateModule
  ]
})
export class PasswordRecoverComponent implements OnInit {
  recoverForm = this.fb.nonNullable.group(
    {
      resetToken: ['', Validators.required],
      password: ['', Validators.required],
      passwordRepeat: ['', Validators.required]
    },
    { validators: [createCompareValidator('password', 'passwordRepeat')] }
  );

  constructor(
    public loginErrorService: LoginErrorService,
    private router: Router,
    private fb: FormBuilder,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loginErrorService.clearError();
  }

  async onSubmit(): Promise<void> {
    if (!this.recoverForm.valid) return;

    const success = await this.authService.passwordRecover(this.recoverForm.value as PasswordResetTokenForm);
    if (success) {
      this.router.navigate([routePaths.login]);
    }
  }
}
