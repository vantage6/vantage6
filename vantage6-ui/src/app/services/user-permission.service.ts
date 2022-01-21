import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

import { arrayContainsObjWithId, deepcopy } from '../utils';

import { TokenStorageService } from './token-storage.service';
import { UserService } from './api/user.service';
import { RuleService } from './api/rule.service';
import { Rule } from '../interfaces/rule';
import { Role } from '../interfaces/role';
import { EMPTY_USER, User } from '../interfaces/user';

const PERMISSION_KEY = 'permissions-user';

@Injectable({
  providedIn: 'root',
})
export class UserPermissionService {
  user: User = EMPTY_USER;
  userBhs = new BehaviorSubject<User>(this.user);
  userRoles: Role[] = [];
  userRules: Rule[] = [];
  userExtraRules: Rule[] = [];
  all_rules: Rule[] = [];

  constructor(
    private tokenStorage: TokenStorageService,
    private userService: UserService,
    private ruleService: RuleService
  ) {
    this.setup();
  }

  async setup(): Promise<void> {
    // request all existing rules
    this.all_rules = await this.ruleService.getAllRules();

    // get user information
    let user_info = this.tokenStorage.getUserInfo();
    if (Object.keys(user_info).length !== 0) {
      this.setUserPermissions(user_info);
    }
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

  // TODO remove function (use similar function from userService!)
  getUser(): Observable<User> {
    return this.userBhs.asObservable();
  }

  getPermissionSubset(
    permissions: Rule[],
    operation: string,
    resource: string,
    scope: string
  ): Rule[] {
    return permissions.filter(
      (p: Rule) =>
        (p.operation === operation || operation === '*') &&
        (p.resource === resource || resource === '*') &&
        (p.scope === scope || scope === '*')
    );
  }

  hasPermission(operation: string, resource: string, scope: string): boolean {
    let permissions: Rule[] = this.getPermissions();
    if (operation == '*' && resource == '*' && scope == '*') {
      // no permissions required: return true even if user has 0 permissions
      return true;
    }
    // filter user permissions. If any are left that fulfill permission
    // criteria, user has permission
    return (
      this.getPermissionSubset(permissions, operation, resource, scope).length >
      0
    );
  }

  can(operation: string, resource: string, org_id: number | null): boolean {
    return (
      this.hasPermission(operation, resource, 'global') ||
      (org_id === this.user.organization_id &&
        this.hasPermission(operation, resource, 'organization'))
    );
  }

  getAvailableRules(type: string, resource: string, scope: string): Rule[] {
    return this.getPermissionSubset(this.all_rules, type, resource, scope);
  }

  isRuleAssigned(sought_rule: Rule, available_rules: Rule[]): boolean {
    return arrayContainsObjWithId(sought_rule.id, available_rules);
  }

  isRuleInRoles(sought_rule: Rule, available_roles: Role[]): boolean {
    for (let role of available_roles) {
      if (this.isRuleAssigned(sought_rule, role.rules)) {
        return true;
      }
    }
    return false;
  }

  public async setUserPermissions(user_info: any) {
    // find the user id
    let user_id = user_info.user_url.split('/').pop();
    if (user_id === undefined) {
      return;
    }

    // request the rules for the current user
    let user = await this.userService.getUser(user_id);
    this.userBhs.next(user);
    console.log(user);

    await this._setPermissions(user, this.all_rules);
  }

  private async _setPermissions(user: User, all_rules: Rule[]) {
    // remove any existing rules that may be present
    this.userRules = [];
    this.userRoles = [];

    // add rules from the user rules and roles
    this.userRules = [];
    this.userRules.push(...deepcopy(user.rules));
    for (let role of user.roles) {
      this.userRules.push(...role.rules);
    }
    // remove double rules
    this.userRules = [...new Set(this.userRules)];

    // save permissions
    this.savePermissions(this.userRules);
  }

  canAssignRole(role: Role): boolean {
    // check if logged in user can assign this role

    // never allow assignment of predefined node and container roles
    if (role.name === 'container' || role.name === 'node') {
      return false;
    }
    // check if user has all the rules for this role themselves
    for (let rule of role.rules) {
      if (!arrayContainsObjWithId(rule.id, this.userRules)) {
        return false;
      }
    }
    return true;
  }
}
