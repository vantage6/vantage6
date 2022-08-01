import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

const TOKEN_KEY = 'auth-token';
const REFRESH_TOKEN_KEY = 'refresh-token';
const USER_KEY = 'auth-user';

@Injectable({
  providedIn: 'root',
})
export class TokenStorageService {
  loggedIn = false;
  loggedInBhs = new BehaviorSubject<boolean>(false);

  constructor() {
    // FIXME this is not secure enough I think, token might just have non-valid value
    this.loggedIn = this.getToken() != null;
    this.loggedInBhs.next(this.loggedIn);
  }

  public setLoginData(data: any) {
    this.saveToken(data.access_token);
    this.saveToken(data.refresh_token, REFRESH_TOKEN_KEY);
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

  public deleteToken(key: string = TOKEN_KEY): void {
    window.sessionStorage.removeItem(key);
  }

  public saveToken(token: string, key: string = TOKEN_KEY): void {
    this.deleteToken(key);
    window.sessionStorage.setItem(key, token);
  }

  public getToken(): string | null {
    return window.sessionStorage.getItem(TOKEN_KEY);
  }

  public getRefreshToken(): string | null {
    return window.sessionStorage.getItem(REFRESH_TOKEN_KEY);
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
