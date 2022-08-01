import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { SignOutService } from 'src/app/services/common/sign-out.service';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  constructor(
    private http: HttpClient,
    private signOutService: SignOutService
  ) {}

  login(username: string, password: string): Observable<any> {
    // ensure cached data is cleared before login
    this.signOutService.clearDataServices();
    // login
    return this.http.post<any>(environment.api_url + '/token/user', {
      username,
      password,
    });
  }
}
