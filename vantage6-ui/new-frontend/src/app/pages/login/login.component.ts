import { Component } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  loginForm = this.fb.group({
    username: [null, Validators.required],
    password: [null, Validators.required]
  });

  constructor(private fb: FormBuilder) {}

  onSubmit(): void {
    if (!this.loginForm.valid) return;

    //TODO: Login
  }
}
