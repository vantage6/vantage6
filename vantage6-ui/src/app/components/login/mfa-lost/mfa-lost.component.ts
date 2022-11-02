import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { AuthService } from 'src/app/auth/services/auth.service';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-mfa-lost',
  templateUrl: './mfa-lost.component.html',
  styleUrls: ['./mfa-lost.component.scss'],
})
export class MfaLostComponent implements OnInit {
  form: any = {};
  executed_request = false;
  request_msg: string = '';

  constructor(private http: HttpClient, private authService: AuthService) {}

  ngOnInit(): void {}

  async onSubmit(): Promise<void> {
    // request email to reset 2fa
    let response = await this.http
      .post<any>(environment.api_url + '/recover/2fa/lost', {
        username: this.authService.username,
        password: this.authService.password,
      })
      .toPromise();

    if (response.msg) {
      this.executed_request = true;
      this.request_msg = response.msg;
    }
  }
}
