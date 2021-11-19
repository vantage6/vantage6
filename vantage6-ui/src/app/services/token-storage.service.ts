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

  constructor() {
    // FIXME this is not secure enough I think, token might just have non-valid value
    this.loggedIn = this.getToken() != null;
    this.loggedInBhs.next(this.loggedIn);
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
