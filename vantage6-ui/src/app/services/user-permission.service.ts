import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';

import { TokenStorageService } from './token-storage.service';
import { environment } from 'src/environments/environment';

type Permission = { type: string; resource: string; scope: string };

@Injectable({
  providedIn: 'root',
})
export class UserPermissionService {
  userUrl: string = '';
  userRules: Permission[] = [];
  userRulesBhs = new BehaviorSubject<Permission[]>([]);
  userIdBhs = new BehaviorSubject<number>(0);

  constructor(
    private http: HttpClient,
    private tokenStorage: TokenStorageService
  ) {
    this.setup();
    // TODO ensure that this doesn't finish until the tokenstorage service has provided
    // the required data
  }

  setup(): void {
    let user = this.tokenStorage.getUserInfo();
    // if user is logged in, set their properties
    if (Object.keys(user).length !== 0) {
      this._setUserUrl(user);
      this.setUserPermissions();
    }
  }

  getUserRules(): Observable<Permission[]> {
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
  }

  hasPermission(type: string, resource: string, scope: string): boolean {
    if (type == '*' && resource == '*' && scope == '*') {
      // no permissions required: return true even if user has 0 permissions
      return true;
    }
    // filter user permissions. If any are left that fulfill permission
    // criteria, user has permission
    const relevant_permissions = this.userRules.filter(
      (p: any) =>
        (p.type === type || type === '*') &&
        (p.resource === resource || resource === '*') &&
        (p.scope === scope || scope === '*')
    );
    return relevant_permissions.length > 0;
  }

  private _setUserUrl(user: any): void {
    this.userUrl = user.user_url;
    let userId = this.userUrl.split('/').pop();
    if (userId !== undefined) this.userIdBhs.next(parseInt(userId));
  }

  public setUserPermissions(): void {
    // request the rules for the current user
    let req_userRules = this.http.get<any>(
      environment.server_url + this.userUrl
    );
    // request description of all rules
    let req_all_rules = this.http.get<any>(environment.api_url + '/rule');

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
        // match the rule descriptions with the current user rule id
        let rule_descr = all_rules.find((r: any) => r.id === rule.id);
        // add new permission
        var new_rule: Permission = {
          type: rule_descr.operation.toLowerCase(),
          resource: rule_descr.name.toLowerCase(),
          scope: rule_descr.scope.toLowerCase(),
        };
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
    this.http.get<any>(environment.server_url + role.link).subscribe(
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
