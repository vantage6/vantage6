import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { Router } from '@angular/router';

const AUTH_API = 'http://localhost:5000/api/';
const TOKEN_KEY = 'auth-token';
const USER_KEY = 'auth-user';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  loggedIn = false;
  loggedInBhs = new BehaviorSubject<boolean>(false);
  isLoginFailed = false;
  errorMessage = new BehaviorSubject<string>('');

  constructor(private http: HttpClient, private router: Router) {
    if (this.getToken()) {
      this.loggedIn = true;
      this.loggedInBhs.next(this.loggedIn);
    }
  }

  login(username: string, password: string): void {
    this.http
      .post<any>(AUTH_API + 'token/user', {
        username,
        password,
      })
      .subscribe(
        (data) => {
          this.saveToken(data.access_token);
          this.saveUser(data);

          this.isLoginFailed = false;
          this.loggedIn = true;
          this.loggedInBhs.next(true);

          // after login, go to home
          this.router.navigateByUrl('/home');
        },
        (err) => {
          this.errorMessage.next(err.error.msg);
          this.isLoginFailed = true;
          this.loggedIn = false;
        }
      );
  }

  getErrorMessage(): Observable<string> {
    return this.errorMessage.asObservable();
  }

  isLoggedIn(): Observable<boolean> {
    return this.loggedInBhs.asObservable();
  }

  signOut(): void {
    this.loggedIn = false;
    this.loggedInBhs.next(false);
    window.sessionStorage.clear();
  }

  public saveToken(token: string): void {
    window.sessionStorage.removeItem(TOKEN_KEY);
    window.sessionStorage.setItem(TOKEN_KEY, token);
  }

  public getToken(): string | null {
    return window.sessionStorage.getItem(TOKEN_KEY);
  }

  public saveUser(user: any): void {
    window.sessionStorage.removeItem(USER_KEY);
    window.sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  public getUser(): any {
    const user = window.sessionStorage.getItem(USER_KEY);
    if (user) {
      return JSON.parse(user);
    }

    return {};
  }
}
