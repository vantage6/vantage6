import { Injectable } from '@angular/core';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';

import { TokenStorageService } from './token-storage.service';
import { UserService } from './api/user.service';
import { RuleService } from './api/rule.service';
import { RoleService } from './api/role.service';
import { Rule } from '../interfaces/rule';

const PERMISSION_KEY = 'permissions-user';

@Injectable({
  providedIn: 'root',
})
export class UserPermissionService {
  userId: number = 0;
  userRules: Rule[] = [];
  userIdBhs = new BehaviorSubject<number>(0);
  allRules: Rule[] = [];
  allRulesBhs = new BehaviorSubject<Rule[]>([]);

  constructor(
    private tokenStorage: TokenStorageService,
    private userService: UserService,
    private ruleService: RuleService,
    private roleService: RoleService
  ) {
    this.setup();
  }

  public savePermissions(permissions: any[]): void {
    window.sessionStorage.removeItem(PERMISSION_KEY);
    window.sessionStorage.setItem(PERMISSION_KEY, JSON.stringify(permissions));
  }

  public getPermissions(): Rule[] {
    let perm_text = window.sessionStorage.getItem(PERMISSION_KEY);
    if (perm_text === null) {
      return [];
    } else {
      let permissions: Rule[] = JSON.parse(perm_text);
      return permissions;
    }
  }

  setup(): void {
    let user = this.tokenStorage.getUserInfo();
    // if user is logged in, set their properties
    if (Object.keys(user).length !== 0) {
      this._setUserId(user);
      this.setUserPermissions();
    }
  }

  getUserId(): Observable<number> {
    return this.userIdBhs.asObservable();
  }

  getRuleDescriptions(): Observable<Rule[]> {
    return this.allRulesBhs.asObservable();
  }

  getPermissionSubset(
    permissions: Rule[],
    type: string,
    resource: string,
    scope: string
  ): Rule[] {
    return permissions.filter(
      (p: any) =>
        (p.type === type || type === '*') &&
        (p.resource === resource || resource === '*') &&
        (p.scope === scope || scope === '*')
    );
  }

  hasPermission(type: string, resource: string, scope: string): boolean {
    let permissions: Rule[] = this.getPermissions();
    if (type == '*' && resource == '*' && scope == '*') {
      // no permissions required: return true even if user has 0 permissions
      return true;
    }
    // filter user permissions. If any are left that fulfill permission
    // criteria, user has permission
    return (
      this.getPermissionSubset(permissions, type, resource, scope).length > 0
    );
  }

  getAvailableRules(type: string, resource: string, scope: string): Rule[] {
    return this.getPermissionSubset(this.allRules, type, resource, scope);
  }

  private _setUserId(user: any): void {
    let userId = user.user_url.split('/').pop();
    if (userId !== undefined) {
      this.userId = userId;
      this.userIdBhs.next(parseInt(userId));
    }
  }

  public setUserPermissions(): void {
    // request the rules for the current user
    let req_userRules = this.userService.get(this.userId);

    // request description of all rules
    let req_all_rules = this.ruleService.list();

    // join user rules and all rules to get user permissions
    forkJoin([req_userRules, req_all_rules]).subscribe(
      (data) => {
        let userRules = data[0];
        let all_rules = data[1];
        this._setPermissions(userRules, all_rules);
        this._setAllRules(all_rules);
      },
      (err) => {
        // TODO raise error if user permissions cannot be determined
        console.log(err);
      }
    );
  }

  private _setAllRules(all_rules: any[]) {
    this.allRules = [];
    for (let rule of all_rules) {
      this.allRules.push({
        id: rule.id,
        type: rule.operation.toLowerCase(),
        resource: rule.name.toLowerCase(),
        scope: rule.scope.toLowerCase(),
      });
    }
    this.allRulesBhs.next(this.allRules);
  }

  private async _setPermissions(userRules: any, all_rules: any) {
    // remove any existing rules that may be present
    this.userRules = [];

    // add rules from the user rules and roles
    await this._setRules(userRules, all_rules);

    // remove double rules
    this.userRules = [...new Set(this.userRules)];

    // save permissions
    this.savePermissions(this.userRules);
  }

  private async _setRules(userRules: any, all_rules: any) {
    await Promise.all([
      this._addRules(userRules.rules, all_rules),
      this._addRoles(userRules.roles, all_rules),
    ]);
  }

  private async _addRules(rules: any, all_rules: any) {
    if (rules !== null) {
      rules.forEach((rule: any) => {
        // match the rule descriptions with the current user rule id
        let rule_descr = all_rules.find((r: any) => r.id === rule.id);
        // add new permission
        var new_rule: Rule = {
          id: rule.id,
          type: rule_descr.operation.toLowerCase(),
          resource: rule_descr.name.toLowerCase(),
          scope: rule_descr.scope.toLowerCase(),
        };
        this.userRules.push(new_rule);
      });
    }
  }

  private async _addRoles(roles: any, all_rules: any) {
    // Add rules from each role to the existing rules
    await Promise.all(
      roles.map(async (role: any) => {
        if (role !== null) {
          await this._addRulesForRole(role, all_rules);
        }
      })
    );
  }

  private async _addRulesForRole(role: any, all_rules: any) {
    let response = await this.roleService.get(role.id).toPromise();

    await this._addRules(response.rules, all_rules);
  }
}
