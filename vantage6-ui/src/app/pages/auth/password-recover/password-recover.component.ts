import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { PasswordResetTokenForm } from 'src/app/models/forms/login-form.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { LoginErrorService } from 'src/app/services/login-error.service';

@Component({
  selector: 'app-password-recover',
  templateUrl: './password-recover.component.html',
  styleUrls: ['./password-recover.component.scss']
})
export class PasswordRecoverComponent implements OnInit {
  recoverForm = this.fb.nonNullable.group({
    resetToken: ['', Validators.required],
    password: ['', Validators.required],
    passwordRepeat: ['', Validators.required]
  });

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
