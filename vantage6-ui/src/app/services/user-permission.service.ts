import { Injectable } from '@angular/core';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';

import { arrayContainsObjWithId, deepcopy, getById } from '../utils';

import { TokenStorageService } from './token-storage.service';
import { UserService } from './api/user.service';
import { RuleService } from './api/rule.service';
import { RoleService } from './api/role.service';
import {
  Rule,
  RuleGroup,
  Operation,
  Scope,
  Resource,
} from '../interfaces/rule';
import { Role } from '../interfaces/role';
import { EMPTY_USER, User } from '../interfaces/user';
import { ConvertJsonService } from './convert-json.service';

const PERMISSION_KEY = 'permissions-user';

@Injectable({
  providedIn: 'root',
})
export class UserPermissionService {
  user: User = EMPTY_USER;
  userBhs = new BehaviorSubject<User>(this.user);
  userId: number = 0;
  userRoles: Role[] = [];
  userRules: Rule[] = [];
  userExtraRules: Rule[] = [];
  allRules: Rule[] = [];
  allRulesBhs = new BehaviorSubject<Rule[]>([]);
  rule_groups: RuleGroup[] = [];

  constructor(
    private tokenStorage: TokenStorageService,
    private userService: UserService,
    private ruleService: RuleService,
    private roleService: RoleService,
    private convertJsonService: ConvertJsonService
  ) {
    this.setup();
  }

  setup(): void {
    let user = this.tokenStorage.getUserInfo();
    // if user is logged in, set their properties
    if (Object.keys(user).length !== 0) {
      this._setUserId(user);
      this.setUserPermissions();
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

  getUser(): Observable<User> {
    return this.userBhs.asObservable();
  }

  getRuleDescriptions(): Observable<Rule[]> {
    return this.allRulesBhs.asObservable();
  }

  getRuleGroupsCopy(): RuleGroup[] {
    return JSON.parse(JSON.stringify(this.rule_groups));
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
    return this.getPermissionSubset(this.allRules, type, resource, scope);
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

  private _setUserId(user: any): void {
    let userId = user.user_url.split('/').pop();
    if (userId !== undefined) {
      this.userId = userId;
    }
  }

  public setUserPermissions() {
    // request the rules for the current user
    let req_userRules = this.userService.get(this.userId);

    // request description of all rules
    let req_all_rules = this.ruleService.list();

    // join user rules and all rules to get user permissions
    forkJoin([req_userRules, req_all_rules]).subscribe(
      (data) => {
        let user_data = data[0];
        let all_rules = data[1];
        this.allRules = this._setAllRules(all_rules);
        this._setPermissions(user_data, this.allRules);
        this._setRuleGroups();
      },
      (err) => {
        // TODO raise error if user permissions cannot be determined
        console.log(err);
      }
    );
  }

  private _setAllRules(all_rules: any[]): Rule[] {
    let allRules = [];
    for (let rule of all_rules) {
      allRules.push({
        id: rule.id,
        operation: rule.operation.toLowerCase(),
        resource: rule.name.toLowerCase(),
        scope: rule.scope.toLowerCase(),
      });
    }
    this.allRulesBhs.next(allRules);
    return allRules;
  }

  _sortRules(rules: Rule[]): Rule[] {
    const resource_order = Object.values(Resource);
    const scope_order = Object.values(Scope);
    const operation_order = Object.values(Operation);
    return rules.sort((a, b) => {
      if (a.resource !== b.resource) {
        return (
          resource_order.indexOf(a.resource) -
          resource_order.indexOf(b.resource)
        );
      } else if (a.scope !== b.scope) {
        return scope_order.indexOf(a.scope) - scope_order.indexOf(b.scope);
      } else {
        return (
          operation_order.indexOf(a.operation) -
          operation_order.indexOf(b.operation)
        );
      }
    });
  }

  _newRuleGroup(rule: Rule): RuleGroup {
    return {
      resource: rule.resource,
      scope: rule.scope,
      rules: [rule],
    };
  }

  _makeRuleGroups(): RuleGroup[] {
    let rule_groups: RuleGroup[] = [];
    let current_rule_group: RuleGroup | undefined = undefined;
    for (let rule of this.allRules) {
      if (current_rule_group === undefined) {
        // first rule: make new rule group
        current_rule_group = this._newRuleGroup(rule);
      } else if (
        current_rule_group.resource === rule.resource &&
        current_rule_group.scope === rule.scope
      ) {
        // the rule is in the same group as previous rule
        current_rule_group.rules.push(rule);
      } else {
        // New Rule group!
        // First, save the previous rule group
        rule_groups.push(deepcopy(current_rule_group));

        // start new rule group
        current_rule_group = this._newRuleGroup(rule);
      }
    }
    // add last rule group
    if (current_rule_group !== undefined) {
      rule_groups.push(deepcopy(current_rule_group));
    }
    return rule_groups;
  }

  _setRuleGroups(): void {
    // sort rules by resource, then scope, then operation
    this.allRules = this._sortRules(this.allRules);

    // divide sorted rules in groups
    this.rule_groups = this._makeRuleGroups();
  }

  private async _setPermissions(user_data: any, all_rules: Rule[]) {
    // remove any existing rules that may be present
    this.userRules = [];
    this.userRoles = [];

    // add rules from the user rules and roles
    await this._setRules(user_data, all_rules);

    // remove double rules
    this.userRules = [...new Set(this.userRules)];

    // save permissions
    this.savePermissions(this.userRules);

    // set user
    this._setUser(user_data);
  }

  private _setUser(user_data: any) {
    // set the logged in user
    this.user = this.convertJsonService.getUser(
      user_data,
      this.userRoles,
      this.allRules
    );
    this.userBhs.next(this.user);
  }

  private async _setRules(user_data: any, all_rules: Rule[]) {
    await Promise.all([
      this._addRules(user_data.rules, all_rules),
      this._addRoles(user_data.roles, all_rules),
    ]);
  }

  private async _addRules(rules_json: any, all_rules: Rule[]) {
    if (rules_json !== null) {
      rules_json.forEach((rule_json: any) => {
        // match the rule descriptions with the current user rule id
        let rule = getById(all_rules, rule_json.id);
        // add new permission
        this.userRules.push(rule);
      });
    }
  }

  private async _addRoles(roles: any, all_rules: Rule[]) {
    // Add rules from each role to the existing rules
    await Promise.all(
      roles.map(async (role: any) => {
        if (role !== null) {
          await this._addRulesForRole(role, all_rules);
        }
      })
    );
  }

  private async _addRulesForRole(role: any, all_rules: Rule[]) {
    let response = await this.roleService.get(role.id).toPromise();
    this.userRoles.push(this.convertJsonService.getRole(response, all_rules));

    await this._addRules(response.rules, all_rules);
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
