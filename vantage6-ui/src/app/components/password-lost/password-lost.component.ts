import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-password-lost',
  templateUrl: './password-lost.component.html',
  styleUrls: ['./password-lost.component.scss'],
})
export class PasswordLostComponent implements OnInit {
  form: any = {
    username: null,
    email: null,
  };
  executed_request = false;
  request_msg: string = '';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {}

  has_double_input(): boolean {
    // check if both username and password have been define
    const { username, email } = this.form;
    return username && email;
  }

  has_valid_input(): boolean {
    // one has to be defined but not the other
    const { username, email } = this.form;
    return Boolean(!(username && email) && (username || email));
  }

  async onSubmit(): Promise<void> {
    const { username, email } = this.form;

    let params: any = {};
    if (username) params['username'] = username;
    else params['email'] = email;

    let response = await this.http
      .post<any>(environment.api_url + '/recover/lost', params)
      .toPromise();

    if (response.msg) {
      this.executed_request = true;
      this.request_msg = response.msg;
    }
  }
}
