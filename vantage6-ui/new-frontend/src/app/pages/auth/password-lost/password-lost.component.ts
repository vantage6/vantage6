import { Component } from '@angular/core';
import { FormBuilder, FormGroup, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';

@Component({
  selector: 'app-password-lost',
  templateUrl: './password-lost.component.html',
  styleUrls: ['./password-lost.component.scss']
})
export class PasswordLostComponent {
  // TODO clean up
  private emailOrUsername(group: FormGroup): ValidationErrors | null {
    const email = group.controls['email'].value;
    const username = group.controls['username'].value;
    const hasAtLeastOne = email || username;
    return hasAtLeastOne
      ? null
      : {
          emailOrUsername: true
        };
  }
  // private atLeastOne =
  // (validator: ValidatorFn, controls: string[] | null = null) =>
  // (group: FormGroup): ValidationErrors | null => {
  //   if (!controls) {
  //     controls = Object.keys(group.controls);
  //   }

  //   const hasAtLeastOne = group && group.controls && controls.some((k) => !validator(group.controls[k]));

  //   return hasAtLeastOne
  //     ? null
  //     : {
  //         atLeastOne: true
  //       };
  // };

  forgotPasswordForm = this.fb.group(
    {
      username: [''],
      email: ['']
    },
    { validator: this.emailOrUsername }
  );
  executed_request = false;
  responseMsg = '';
  routes = routePaths;

  constructor(
    private router: Router,
    private fb: FormBuilder,
    private authService: AuthService
  ) {}

  async onSubmit(): Promise<void> {
    if (!this.forgotPasswordForm.valid) return;

    const responseMsg = await this.authService.passwordLost(this.forgotPasswordForm.value);
    if (responseMsg) {
      this.executed_request = true;
      this.responseMsg = responseMsg;
    }
  }
}
