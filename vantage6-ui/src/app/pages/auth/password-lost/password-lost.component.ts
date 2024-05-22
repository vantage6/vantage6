import { Component, OnInit } from '@angular/core';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { LoginErrorService } from 'src/app/services/login-error.service';

@Component({
  selector: 'app-password-lost',
  templateUrl: './password-lost.component.html',
  styleUrls: ['./password-lost.component.scss']
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
