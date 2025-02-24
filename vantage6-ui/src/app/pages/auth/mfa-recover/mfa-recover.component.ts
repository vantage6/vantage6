import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MFAResetTokenForm } from 'src/app/models/forms/login-form.model';
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
    selector: 'app-mfa-recover',
    templateUrl: './mfa-recover.component.html',
    styleUrls: ['./mfa-recover.component.scss'],
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
        NgIf,
        AlertComponent,
        TranslateModule
    ]
})
export class MfaRecoverComponent implements OnInit {
  recoverForm = this.fb.nonNullable.group({
    resetToken: ['', Validators.required]
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

    const success = await this.authService.MFARecover(this.recoverForm.value as MFAResetTokenForm);
    if (success) {
      this.router.navigate([routePaths.setupMFA]);
    }
  }
}
