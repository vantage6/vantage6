import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-password-recover',
  templateUrl: './password-recover.component.html',
  styleUrls: ['./password-recover.component.scss'],
})
export class PasswordRecoverComponent implements OnInit {
  form: any = {
    reset_token: null,
    password: null,
    password_repeated: null,
  };
  error_message: string = '';
  api_call_complete: boolean = false;

  constructor(private http: HttpClient, private router: Router) {}

  ngOnInit(): void {}

  onSubmit(): void {
    const { reset_token, password, password_repeated } = this.form;

    // TODO ensure form is not submitted if this is not the case, instead of
    // handling the error here
    if (password !== password_repeated) return;

    this.change_password(reset_token, password);
  }

  async change_password(reset_token: string, password: string): Promise<void> {
    this.http
      .post(environment.api_url + '/recover/reset', {
        password: password,
        reset_token: reset_token,
      })
      .subscribe(
        (data) => {
          // after resetting password successfully, go to login page
          this.router.navigateByUrl('/login');
        },
        (err) => {
          this.api_call_complete = true;
          if (err.status === 0) {
            this.error_message = 'Cannot connect to server!';
          } else {
            this.error_message = err.error.msg;
          }
        }
      );
  }
}
