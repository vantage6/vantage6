import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from 'src/app/auth/services/auth.service';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-mfa-recover',
  templateUrl: './mfa-recover.component.html',
  styleUrls: ['./mfa-recover.component.scss'],
})
export class MfaRecoverComponent implements OnInit {
  form: any = {
    reset_token: null,
  };
  error_message: string = '';
  api_call_complete: boolean = false;

  constructor(
    private http: HttpClient,
    private router: Router,
    private authService: AuthService
  ) {}

  ngOnInit(): void {}

  onSubmit(): void {
    const { reset_token } = this.form;

    this.reset_mfa(reset_token);
  }

  reset_mfa(reset_token: string) {
    this.http
      .post(environment.api_url + '/recover/2fa/reset', {
        reset_token: reset_token,
      })
      .subscribe(
        (data: any) => {
          // set data to generate QR code
          this.authService.qr_uri = data['qr_uri'];
          this.authService.otp_code = data['otp_secret'];
          // after resetting password successfully, go to login page
          this.router.navigateByUrl('/setup_mfa');
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
