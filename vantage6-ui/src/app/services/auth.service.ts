import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { Location } from '@angular/common';

const AUTH_API = 'http://localhost:5000/api/';
const TOKEN_KEY = 'auth-token';
const USER_KEY = 'auth-user';

const httpOptions = {
  headers: new HttpHeaders({ 'Content-Type': 'application/json' }),
};

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  loggedIn = false;
  loggedInBhs = new BehaviorSubject<boolean>(false);
  isLoginFailed = false;
  errorMessage = new BehaviorSubject<string>('');

  constructor(private http: HttpClient, private location: Location) {}

  login(username: string, password: string): void {
    console.log('logging in auth service');
    this.http
      .post<any>(AUTH_API + 'token/user', {
        username,
        password,
      })
      .subscribe(
        (data) => {
          console.log('data');
          console.log(data);
          this.saveToken(data.access_token);
          this.saveUser(data);

          this.isLoginFailed = false;
          this.loggedIn = true;
          this.loggedInBhs.next(true);

          // TODO if last page was already login page, go to home
          // go back to last page before login
          // window.location.reload();
          this.location.back();
        },
        (err) => {
          console.log('err');
          console.log(err);
          this.errorMessage.next(err.error.msg);
          console.log(this.errorMessage);
          this.isLoginFailed = true;
          this.loggedIn = false;
        }
      );
  }

  getErrorMessage(): Observable<string> {
    return this.errorMessage.asObservable();
  }

  isLoggedIn(): Observable<boolean> {
    console.log(this.loggedIn);
    console.log(
      'isLoggedIn() returns',
      this.loggedInBhs.asObservable()
      // this.loggedIn
    );
    return this.loggedInBhs.asObservable();
  }

  // TODO logout procedure should be here

  // register(username: string, email: string, password: string): Observable<any> {
  //   return this.http.post(AUTH_API + 'signup', {
  //     username,
  //     email,
  //     password
  //   }, httpOptions);
  // }

  signOut(): void {
    this.loggedIn = false;
    this.loggedInBhs.next(false);
    console.log('Logging out in signOut()');
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
