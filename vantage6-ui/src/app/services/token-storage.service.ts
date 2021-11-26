import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';

import { API_URL, SERVER_URL } from '../constants';

const TOKEN_KEY = 'auth-token';
const USER_KEY = 'auth-user';

@Injectable({
  providedIn: 'root',
})
export class TokenStorageService {
  loggedIn = false;
  loggedInBhs = new BehaviorSubject<boolean>(false);
  userUrl: string = '';
  userRules: string[] = [];
  userRulesBhs = new BehaviorSubject<string[]>([]);

  constructor(private http: HttpClient) {
    // FIXME this is not secure enough I think, token might just have non-valid value
    this.loggedIn = this.getToken() != null;
    this.loggedInBhs.next(this.loggedIn);
  }

  public async setLoginData(data: any) {
    this.saveToken(data.access_token);
    this.saveUserId(data);
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

  getUserRules(): Observable<string[]> {
    return this.userRulesBhs.asObservable();
  }

  public saveToken(token: string): void {
    window.sessionStorage.removeItem(TOKEN_KEY);
    window.sessionStorage.setItem(TOKEN_KEY, token);
  }

  public getToken(): string | null {
    return window.sessionStorage.getItem(TOKEN_KEY);
  }

  public saveUserId(user: any): void {
    this.userUrl = user.user_url;
  }

  public setUserPermissions(): void {
    // request the rules for the current user
    let req_userRules = this.http.get<any>(SERVER_URL + this.userUrl);
    // request description of all rules
    let req_all_rules = this.http.get<any>(API_URL + '/rule');

    // join user rules and all rules to get user permissions
    forkJoin([req_userRules, req_all_rules]).subscribe(
      (data) => {
        let userRules = data[0];
        let all_rules = data[1];
        this._setPermissions(userRules, all_rules);
      },
      (err) => {
        // TODO raise error if user permissions cannot be determined
        console.log(err);
      }
    );
  }

  private async _setPermissions(userRules: any, all_rules: any) {
    // remove any existing rules that may be present
    this.userRules = [];

    // add rules from the user rules and roles
    await this._setRules(userRules, all_rules);

    // remove double rules
    this.userRules = [...new Set(this.userRules)];
    this.userRulesBhs.next(this.userRules);
  }

  private async _setRules(userRules: any, all_rules: any) {
    this._addRules(userRules.rules, all_rules);
    this._addRoles(userRules.roles, all_rules);
  }

  private _addRules(rules: any, all_rules: any) {
    if (rules !== null) {
      rules.forEach((rule: any) => {
        let rule_descr = all_rules.find((r: any) => r.id === rule.id);
        var new_rule: string =
          `${rule_descr.operation}_${rule_descr.name}_${rule_descr.scope}`.toLowerCase();
        this.userRules.push(new_rule);
      });
    }
  }

  private _addRoles(roles: any, all_rules: any) {
    // Add rules from each role to the existing rules
    if (roles !== null) {
      roles.forEach((role: any) => {
        this._addRulesForRole(role, all_rules);
      });
    }
  }

  private _addRulesForRole(role: any, all_rules: any): number[] {
    this.http.get<any>(SERVER_URL + role.link).subscribe(
      (data) => {
        this._addRules(data.rules, all_rules);
      },
      (err) => {
        // TODO raise error if user permissions cannot be determined
        console.log(err);
      }
    );
    return [];
  }
}
