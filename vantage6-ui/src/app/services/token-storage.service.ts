import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

const TOKEN_KEY = 'auth-token';
const USER_KEY = 'auth-user';

@Injectable({
  providedIn: 'root',
})
export class TokenStorageService {
  loggedIn = false;
  loggedInBhs = new BehaviorSubject<boolean>(false);

  constructor(private http: HttpClient) {
    // FIXME this is not secure enough I think, token might just have non-valid value
    this.loggedIn = this.getToken() != null;
    this.loggedInBhs.next(this.loggedIn);
    // TODO find way to set user permissions outside of constructor. Probably need to refactor
    //   this.setUserPermissions();
  }

  public setLoginData(data: any) {
    this.saveToken(data.access_token);
    this.saveUserInfo(data);
    this.setLoggedIn(true);
  }

  setLoggedIn(isLoggedIn: boolean) {
    this.loggedIn = isLoggedIn;
    this.loggedInBhs.next(isLoggedIn);
  }

  signOut(): void {
    this.loggedIn = false;
    this.loggedInBhs.next(false);
    window.sessionStorage.clear();
  }

  isLoggedIn(): Observable<boolean> {
    return this.loggedInBhs.asObservable();
  }

  public saveToken(token: string): void {
    window.sessionStorage.removeItem(TOKEN_KEY);
    window.sessionStorage.setItem(TOKEN_KEY, token);
  }

  public getToken(): string | null {
    return window.sessionStorage.getItem(TOKEN_KEY);
  }

  public saveUserInfo(user: any): void {
    window.sessionStorage.removeItem(USER_KEY);
    window.sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  public getUserInfo() {
    const user = window.sessionStorage.getItem(USER_KEY);
    if (user) {
      return JSON.parse(user);
    }
    return {};
  }
}
