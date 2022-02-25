import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

import { arrayContainsObjWithId, deepcopy } from 'src/app/shared/utils';

import { TokenStorageService } from 'src/app/shared/services/token-storage.service';
import { ApiUserService } from 'src/app/services/api/api-user.service';
import { ApiRuleService } from 'src/app/services/api/api-rule.service';
import { Rule } from 'src/app/interfaces/rule';
import { Role } from 'src/app/interfaces/role';
import { EMPTY_USER, User } from 'src/app/interfaces/user';
import { ApiRoleService } from 'src/app/services/api/api-role.service';
import { OpsType, ResType, ScopeType } from 'src/app/shared/enum';

const PERMISSION_KEY = 'permissions-user';

@Injectable({
  providedIn: 'root',
})
export class UserPermissionService {
  user: User = EMPTY_USER;
  userBhs = new BehaviorSubject<User>(this.user);
  userRules: Rule[] = [];
  userExtraRules: Rule[] = [];
  all_rules: Rule[] = [];
  ready = new BehaviorSubject<boolean>(false);

  constructor(
    private tokenStorage: TokenStorageService,
    private userService: ApiUserService,
    private ruleService: ApiRuleService,
    private roleService: ApiRoleService
  ) {
    this.setup();
  }

  async setup(): Promise<void> {
    // request all existing rules
    this.all_rules = await this.ruleService.getAllRules();

    // get user information
    let user_info = this.tokenStorage.getUserInfo();
    if (Object.keys(user_info).length !== 0) {
      await this.setUserPermissions(user_info);
    }
    this.ready.next(true);
  }

  public async savePermissions(permissions: any[]): Promise<void> {
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

  isInitialized(): Observable<boolean> {
    return this.ready.asObservable();
  }

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

  hasPermission(
    operation: OpsType | string,
    resource: ResType | string,
    scope: ScopeType | string
  ): boolean {
    let permissions: Rule[] = this.getPermissions();
    if (
      operation == OpsType.ANY &&
      resource == ResType.ANY &&
      scope == ScopeType.ANY
    ) {
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

  can(
    operation: OpsType | string,
    resource: ResType | string,
    org_id: number | null
  ): boolean {
    return (
      this.hasPermission(operation, resource, ScopeType.GLOBAL) ||
      (org_id === this.user.organization_id &&
        this.hasPermission(operation, resource, ScopeType.ORGANIZATION))
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
    this.user = await this.userService.getUser(user_id);

    await this._setPermissions(this.user, this.all_rules);

    this.userBhs.next(this.user);
  }

  private async _setPermissions(user: User, all_rules: Rule[]) {
    // remove any existing rules that may be present
    this.userRules = [];

    // add rules from the user rules and roles
    this.userRules.push(...deepcopy(user.rules));
    for (let role of user.roles) {
      this.userRules.push(...role.rules);
    }
    // remove double rules
    this.userRules = [...new Set(this.userRules)];

    // save permissions
    await this.savePermissions(this.userRules);
  }

  canAssignRole(role: Role): boolean {
    // check if logged in user can assign this role

    // never allow assignment of predefined node and container roles
    if (role.name === 'container' || role.name === 'node') {
      return false;
    }
    // check if user has all the rules for this role themselves
    for (let rule of role.rules) {
      if (!this.canAssignRule(rule)) {
        return false;
      }
    }
    return true;
  }

  canAssignRule(rule: Rule): boolean {
    return arrayContainsObjWithId(rule.id, this.userRules);
  }

  async getAssignableRoles(
    organization_id: number,
    available_roles: Role[] | null = null
  ): Promise<Role[]> {
    // set which roles currently logged in user can assign
    if (available_roles === null) {
      available_roles = await this.roleService.getOrganizationRoles(
        organization_id,
        true
      );
    }
    let roles_assignable: Role[] = [];
    for (let role of available_roles) {
      if (this.canAssignRole(role)) {
        roles_assignable.push(role);
      }
    }
    return roles_assignable;
  }

  canModifyRulesOtherUser(user: User): boolean {
    for (let role of user.roles) {
      if (!this.canAssignRole(role)) {
        return false;
      }
    }
    for (let rule of user.rules) {
      if (!this.canAssignRule(rule)) {
        return false;
      }
    }
    return true;
  }
}
