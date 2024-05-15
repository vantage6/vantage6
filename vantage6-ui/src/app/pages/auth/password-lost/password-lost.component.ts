import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ValidationErrors } from '@angular/forms';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { LoginErrorService } from 'src/app/services/login-error.service';

@Component({
  selector: 'app-password-lost',
  templateUrl: './password-lost.component.html',
  styleUrls: ['./password-lost.component.scss']
})

export class PasswordLostComponent implements OnInit {
    private email(group: FormGroup): ValidationErrors | null {
      const email = group.controls['email'].value;
      return email ? null : { email: true };
    }

    forgotPasswordForm = this.fb.group(
      { email: [''] },
      { validator: this.email }
    );

    executed_request = false;
    responseMsg = '';
    routes = routePaths;

    constructor(
      public loginErrorService: LoginErrorService,
      private fb: FormBuilder,
      private authService: AuthService
    ) {}

    ngOnInit(): void {
      this.loginErrorService.clearError();
    }

    async onSubmit(): Promise<void> {
      if (!this.forgotPasswordForm.valid) return;
      const responseMsg = await this.authService.passwordLost(this.forgotPasswordForm.value);
      if (responseMsg) {
        this.executed_request = true;
        this.responseMsg = responseMsg;
      }
    }
}
