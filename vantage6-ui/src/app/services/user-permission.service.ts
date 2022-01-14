import { Injectable } from '@angular/core';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';

import { arrayContainsObjWithId, deepcopy } from '../utils';

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
  rule_groups: RuleGroup[] = [];

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
        operation: rule.operation.toLowerCase(),
        resource: rule.name.toLowerCase(),
        scope: rule.scope.toLowerCase(),
      });
    }
    this.allRulesBhs.next(this.allRules);
    this._setRuleGroups();
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
          operation: rule_descr.operation.toLowerCase(),
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
