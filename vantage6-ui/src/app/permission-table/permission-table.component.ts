import { Component, Input, OnChanges, OnInit } from '@angular/core';

import { Role } from '../interfaces/role';
import { Rule, RuleGroup } from '../interfaces/rule';
import { RuleService } from '../services/api/rule.service';

import { UserPermissionService } from '../services/user-permission.service';
import {
  arrayContainsObjWithId,
  containsObject,
  deepcopy,
  isSubset,
  removeArrayDoubles,
  removeMatchedIdFromArray,
} from '../utils';

@Component({
  selector: 'app-permission-table',
  templateUrl: './permission-table.component.html',
  styleUrls: ['./permission-table.component.scss'],
})
export class PermissionTableComponent implements OnInit, OnChanges {
  @Input() given_roles: Role[] = [];
  @Input() given_rules: Rule[] = [];
  @Input() loggedin_user_rules: Rule[] = [];
  @Input() is_edit_mode: boolean = false;
  user_rules: Rule[] = [];
  user_rule_groups: RuleGroup[] = [];
  added_rules: Rule[] = [];

  RESOURCES: string[] = [
    'user',
    'organization',
    'collaboration',
    'role',
    'node',
    'task',
    'result',
    'port',
  ];
  BTN_CLS_PERM: string = 'btn-has-permission';
  BTN_CLS_PERM_FROM_RULE: string = 'btn-has-permission-rule';
  BTN_CLS_NO_PERM: string = 'btn-no-permission';
  BTN_CLS_PART_PERM: string = 'btn-part-permission';
  BTN_CLS_NO_PERM_POSSIBLE: string = 'btn-no-permission-possible';

  constructor(public userPermission: UserPermissionService) {}

  ngOnInit(): void {
    this.setUserRules();
  }

  ngOnChanges(): void {
    this.setUserRules();
  }

  setUserRules(): void {
    this.user_rules = [];
    // add rules for roles
    for (let role of this.given_roles) {
      this.user_rules.push(...role.rules);
    }

    // remove double rules
    this.user_rules = removeArrayDoubles(this.user_rules);

    // signal which rules have been added as part of role
    for (let rule of this.user_rules) {
      rule.is_part_role = true;
    }

    // add any extra rules that were not yet present
    for (let rule of this.given_rules.concat(this.added_rules)) {
      if (!arrayContainsObjWithId(rule.id, this.user_rules)) {
        rule.is_part_role = false;
        this.user_rules.push(deepcopy(rule));
      }
    }

    // make rule groups for permission display
  }

  getClass(type: string, resource: string, scope: string) {
    const user_has = this.userPermission.getPermissionSubset(
      this.user_rules,
      type,
      resource,
      scope
    );

    const default_classes: string = 'btn btn-in-group btn-operation ';
    if (user_has.length > 0) {
      if (this.is_edit_mode && !user_has[0].is_part_role) {
        return default_classes + this.BTN_CLS_PERM_FROM_RULE;
      } else {
        return default_classes + this.BTN_CLS_PERM;
      }
    } else {
      if (this.is_edit_mode) {
        // if in edit mode, check if the logged in user is allowed to give
        // these permissions (only if they have the rule themselves)
        if (this.loggedinUserCanAssign(type, resource, scope)) {
          return default_classes + this.BTN_CLS_NO_PERM;
        } else {
          return default_classes + this.BTN_CLS_NO_PERM_POSSIBLE;
        }
      }
      return default_classes + this.BTN_CLS_NO_PERM;
    }
  }

  getNumRulesLoggedInUser(
    type: string,
    resource: string,
    scope: string
  ): number {
    const loggedin_user_has = this.userPermission.getPermissionSubset(
      this.loggedin_user_rules,
      type,
      resource,
      scope
    );
    return loggedin_user_has.length;
  }

  loggedinUserCanAssign(
    type: string,
    resource: string,
    scope: string
  ): boolean {
    return this.getNumRulesLoggedInUser(type, resource, scope) > 0;
  }

  userHasAssignableRules(user_rules: Rule[], loggedin_rules: Rule[]): boolean {
    return isSubset(loggedin_rules, user_rules);
    // TODO this result is wrong
  }

  getScopeClass(resource: string, scope: string) {
    const user_has = this.userPermission.getPermissionSubset(
      this.user_rules,
      '*',
      resource,
      scope
    );
    const available_rules = this.userPermission.getAvailableRules(
      '*',
      resource,
      scope
    );
    const rules_logged_in_user = this.userPermission.getPermissionSubset(
      this.loggedin_user_rules,
      '*',
      resource,
      scope
    );

    const default_classes: string = 'btn btn-scope ';
    if (
      this.is_edit_mode &&
      this.userHasAssignableRules(rules_logged_in_user, user_has)
    ) {
      return default_classes + this.BTN_CLS_NO_PERM_POSSIBLE;
    } else if (user_has.length === available_rules.length) {
      return default_classes + this.BTN_CLS_PERM;
    } else if (user_has.length > 0) {
      return default_classes + this.BTN_CLS_PART_PERM;
    } else {
      return default_classes + this.BTN_CLS_NO_PERM;
    }
  }

  getScopes(resource: string): string[] {
    if (resource === 'user') {
      return ['own', 'organization', 'global'];
    } else if (resource === 'organization') {
      return ['organization', 'collaboration', 'global'];
    } else {
      return ['organization', 'global'];
    }
  }

  getOperations(resource: string, scope: string): string[] {
    if (
      resource === 'result' ||
      resource === 'port' ||
      (resource === 'organization' && scope === 'collaboration') ||
      (resource === 'collaboration' && scope === 'organization')
    ) {
      return ['view'];
    } else if (resource === 'user' && scope === 'own') {
      return ['view', 'edit', 'delete'];
    } else if (resource === 'organization' && scope === 'organization') {
      return ['view', 'edit'];
    } else if (resource === 'organization' && scope === 'global') {
      return ['view', 'create', 'edit'];
    } else {
      return ['view', 'create', 'edit', 'delete'];
    }
  }

  isDisabled(operation: string, resource: string, scope: string) {
    if (!this.is_edit_mode) {
      return true;
    }
    for (let role of this.given_roles) {
      const user_has = this.userPermission.getPermissionSubset(
        role.rules,
        operation,
        resource,
        scope
      );
      if (
        user_has.length > 0 ||
        !this.loggedinUserCanAssign(operation, resource, scope)
      ) {
        return true;
      }
    }
    return false;
  }

  isDisabledScope(resource: string, scope: string) {
    // disable a scope if the user already has all the rules in their roles
    // that the logged-in user is allowed to assign

    // buttons in view mode are always disabled
    if (!this.is_edit_mode) {
      return true;
    }

    let user_has: Rule[] = [];
    for (let role of this.given_roles) {
      user_has.push(
        ...this.userPermission.getPermissionSubset(
          role.rules,
          '*',
          resource,
          scope
        )
      );
    }

    user_has = removeArrayDoubles(user_has);
    let num_rules_logged_in_user = this.getNumRulesLoggedInUser(
      '*',
      resource,
      scope
    );
    return user_has.length >= num_rules_logged_in_user;
  }

  // TODO add check if logged in user can assign the rules (if scope is added at once)
  select_or_deselect(
    event: any,
    operation: string,
    resource: string,
    scope: string
  ) {
    console.log('select', event);
    let classes: string = event.target.className;
    let available_rules = this.userPermission.getAvailableRules(
      operation,
      resource,
      scope
    );
    if (classes.includes(this.BTN_CLS_PERM)) {
      // Deselect: remove current permissions
      for (let rule of available_rules) {
        // check if it is part of a role, otherwise don't remove it
        let rule_in_roles = false;
        for (let role of this.given_roles) {
          if (containsObject(rule, role.rules)) {
            rule_in_roles = true;
            break;
          }
        }
        if (!rule_in_roles) {
          this.user_rules = removeMatchedIdFromArray(this.user_rules, rule);
          this.added_rules = removeMatchedIdFromArray(this.added_rules, rule);
        }
      }
    } else {
      // Select: add permissions
      for (let rule of available_rules) {
        rule.is_part_role = false;
      }
      this.user_rules.push(...available_rules);
      this.user_rules = removeArrayDoubles(this.user_rules);
      this.added_rules.push(...available_rules);
      this.added_rules = removeArrayDoubles(this.added_rules);
    }
  }
}
