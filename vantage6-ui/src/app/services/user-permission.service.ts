import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';

import { TokenStorageService } from './token-storage.service';
import { API_URL, SERVER_URL } from '../constants';

@Injectable({
  providedIn: 'root',
})
export class UserPermissionService {
  userUrl: string = '';
  userRules: string[] = [];
  userRulesBhs = new BehaviorSubject<string[]>([]);
  userIdBhs = new BehaviorSubject<number>(0);

  constructor(
    private http: HttpClient,
    private tokenStorage: TokenStorageService
  ) {
    this.setup();
  }

  setup(): void {
    this._setUserUrl();
    this.setUserPermissions();
  }

  getUserRules(): Observable<string[]> {
    return this.userRulesBhs.asObservable();
  }

  getUserId(): Observable<number> {
    return this.userIdBhs.asObservable();
  }

  clearPermissions(): void {
    this.userUrl = '';
    this.userRules = [];
    this.userRulesBhs.next([]);
    this.userIdBhs.next(0);
    console.log('all clear');
  }

  private _setUserUrl(): void {
    let user = this.tokenStorage.getUserInfo();
    if (user !== null) {
      this.userUrl = user.user_url;
      let userId = this.userUrl.split('/').pop();
      if (userId !== undefined) this.userIdBhs.next(parseInt(userId));
    } else {
      console.log('Could not find user'); // TODO raise issue
    }
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
