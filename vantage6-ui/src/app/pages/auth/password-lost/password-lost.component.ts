import { Component, OnInit } from '@angular/core';
import { FormGroup, FormControl, Validators, ReactiveFormsModule } from '@angular/forms';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { LoginErrorService } from 'src/app/services/login-error.service';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatButton } from '@angular/material/button';
import { NgIf } from '@angular/common';
import { AlertWithButtonComponent } from '../../../components/alerts/alert-with-button/alert-with-button.component';
import { RouterLink } from '@angular/router';
import { AlertComponent } from '../../../components/alerts/alert/alert.component';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-password-lost',
  templateUrl: './password-lost.component.html',
  styleUrls: ['./password-lost.component.scss'],
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
    MatButton,
    NgIf,
    AlertWithButtonComponent,
    RouterLink,
    AlertComponent,
    TranslateModule
  ]
})
export class PasswordLostComponent implements OnInit {
  forgotPasswordForm = new FormGroup({
    email: new FormControl('', [Validators.required, Validators.email])
  });

  executed_request = false;
  responseMsg = '';
  routes = routePaths;

  constructor(
    public loginErrorService: LoginErrorService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loginErrorService.clearError();
  }

  async onSubmit(): Promise<void> {
    if (!this.forgotPasswordForm.valid) return;

    const emailValue = this.forgotPasswordForm.get('email')?.value;
    if (emailValue) {
      const responseMsg = await this.authService.passwordLost({ email: emailValue });
      if (responseMsg) {
        this.executed_request = true;
        this.responseMsg = responseMsg;
      }
    }
  }
}
