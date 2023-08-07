import { Component } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { LoginForm } from 'src/app/models/forms/login-form.model';
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
    private fb: FormBuilder,
    private authService: AuthService
  ) {}

  onSubmit(): void {
    if (!this.loginForm.valid) return;

    this.authService.login(this.loginForm.value as LoginForm);
  }
}
