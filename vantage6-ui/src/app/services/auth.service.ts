import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { Router } from '@angular/router';

import { API_URL } from '../constants';

const TOKEN_KEY = 'auth-token';
const USER_KEY = 'auth-user';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  // loggedIn = false;
  // loggedInBhs = new BehaviorSubject<boolean>(false);
  // isLoginFailed = false;
  // errorMessage = new BehaviorSubject<string>('');

  constructor(private http: HttpClient, private router: Router) {
    // if (this.getToken()) {
    //   this.loggedIn = true;
    //   this.loggedInBhs.next(this.loggedIn);
    // }
  }

  login(username: string, password: string): Observable<any> {
    return this.http.post<any>(API_URL + 'token/user', {
      username,
      password,
    });
  }

  // getErrorMessage(): Observable<string> {
  //   return this.errorMessage.asObservable();
  // }

  // isLoggedIn(): Observable<boolean> {
  //   return this.loggedInBhs.asObservable();
  // }

  // signOut(): void {
  //   // this.loggedIn = false;
  //   // this.loggedInBhs.next(false);
  //   window.sessionStorage.clear();
  // }
}
