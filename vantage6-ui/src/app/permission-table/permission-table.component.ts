import {
  Component,
  Input,
  OnChanges,
  OnInit,
  Output,
  EventEmitter,
} from '@angular/core';

import { Role } from '../interfaces/role';
import {
  Rule,
  RuleGroup,
  Resource,
  Scope,
  Operation,
} from '../interfaces/rule';
import { RuleService } from '../services/api/rule.service';

import { UserPermissionService } from '../services/user-permission.service';
import {
  arrayContainsObjWithId,
  containsObject,
  deepcopy,
  getIdsFromArray,
  isSubset,
  removeArrayDoubles,
  removeMatchedIdFromArray,
} from '../utils';

@Component({
  selector: 'app-permission-table',
  templateUrl: './permission-table.component.html',
  styleUrls: ['../globals/buttons.scss', './permission-table.component.scss'],
})
export class PermissionTableComponent implements OnInit, OnChanges {
  @Input() given_roles: Role[] = [];
  @Input() given_rules: Rule[] = [];
  @Input() loggedin_user_rules: Rule[] = [];
  @Input() is_edit_mode: boolean = false;
  user_rules: Rule[] = [];
  rule_groups: RuleGroup[] = [];
  added_rules: Rule[] = [];
  current_role_ids: number[] = [];
  @Output() addedRulesChangeEvent = new EventEmitter<Rule[]>();

  BTN_CLS_PERM: string = 'btn-has-permission';
  BTN_CLS_PERM_FROM_RULE: string = 'btn-has-permission-rule';
  BTN_CLS_NO_PERM: string = 'btn-no-permission';
  BTN_CLS_PART_PERM: string = 'btn-part-permission';
  BTN_CLS_NO_PERM_POSSIBLE: string = 'btn-no-permission-possible';

  constructor(
    public userPermission: UserPermissionService,
    private ruleService: RuleService
  ) {}

  ngOnInit(): void {
    this.rule_groups = this.ruleService.getRuleGroupsCopy();
    this.init();
  }

  ngOnChanges(): void {
    if (!this.rolesHaveChanged()) {
      return;
    }
    this.init();
  }

  init(): void {
    this.setUserRules();
  }

  setUserRules(): void {
    // add rules for roles
    this.user_rules = [];
    this.current_role_ids = [];
    for (let role of this.given_roles) {
      this.user_rules.push(...role.rules);
      this.current_role_ids.push(role.id);
    }
    this.user_rules = removeArrayDoubles(this.user_rules);

    // signal which rules have been added as part of role
    for (let rule of this.user_rules) {
      rule.is_part_role = true;
    }

    // add any extra rules that were not yet present
    this.added_rules = this.given_rules.concat(this.added_rules);
    this.added_rules = removeArrayDoubles(this.added_rules);
    for (let rule of this.added_rules) {
      rule.is_part_role = arrayContainsObjWithId(rule.id, this.user_rules);
      if (!rule.is_part_role) {
        this.user_rules.push(deepcopy(rule));
      }
    }
    this.addedRulesChangeEvent.emit(this.added_rules);

    // set properties of rule groups whether rules are assigned, and are part
    // of rules or not
    for (let rule_group of this.rule_groups) {
      for (let rule of rule_group.rules) {
        rule.is_assigned_to_user = this.userPermission.isRuleAssigned(
          rule,
          this.user_rules
        );
        rule.is_part_role = this.userPermission.isRuleInRoles(
          rule,
          this.given_roles
        );
        rule.is_assigned_to_loggedin = this.userPermission.isRuleAssigned(
          rule,
          this.loggedin_user_rules
        );
      }
    }
  }

  rolesHaveChanged(): boolean {
    let new_role_ids = getIdsFromArray(this.given_roles);
    // check if roles are equal
    if (
      new_role_ids.sort().join('') !== this.current_role_ids.sort().join('')
    ) {
      return true;
    }
    return false;
  }

  getClass(rule: Rule) {
    const default_classes: string = 'btn btn-in-group btn-operation ';
    if (rule.is_assigned_to_user) {
      if (this.is_edit_mode && !rule.is_part_role) {
        return default_classes + this.BTN_CLS_PERM_FROM_RULE;
      } else {
        return default_classes + this.BTN_CLS_PERM;
      }
    } else {
      if (this.is_edit_mode) {
        // if in edit mode, check if the logged in user is allowed to give
        // these permissions (only if they have the rule themselves)
        if (rule.is_assigned_to_loggedin) {
          return default_classes + this.BTN_CLS_NO_PERM;
        } else {
          return default_classes + this.BTN_CLS_NO_PERM_POSSIBLE;
        }
      }
      return default_classes + this.BTN_CLS_NO_PERM;
    }
  }

  getScopeClass(rule_group: RuleGroup) {
    const default_classes: string = 'btn btn-scope ';
    if (this.is_edit_mode && this.loggedInUserMissesRules(rule_group)) {
      // signal that logged-in user is not able to assign (all of) these roles
      return default_classes + this.BTN_CLS_NO_PERM_POSSIBLE;
    } else if (this.userHasAllAssignableRules(rule_group)) {
      // has all rules or, if in edit mode, all rules that logged-in user
      // can assign
      return default_classes + this.BTN_CLS_PERM;
    } else if (this.userHasAnyRule(rule_group)) {
      // has part of available permissions
      return default_classes + this.BTN_CLS_PART_PERM;
    } else {
      // has no rules but they can be assigned
      return default_classes + this.BTN_CLS_NO_PERM;
    }
  }

  loggedInUserMissesRules(rule_group: RuleGroup): boolean {
    let logged_in_has_rules = false;
    for (let rule of rule_group.rules) {
      if (rule.is_assigned_to_user && !rule.is_assigned_to_loggedin) {
        return true;
      }
      if (rule.is_assigned_to_loggedin) {
        logged_in_has_rules = true;
      }
    }
    return !logged_in_has_rules;
  }

  userHasAllAssignableRules(rule_group: RuleGroup): boolean {
    for (let rule of rule_group.rules) {
      if (
        !rule.is_assigned_to_user &&
        (!this.is_edit_mode || rule.is_assigned_to_loggedin)
      ) {
        return false;
      }
    }
    return true;
  }

  userHasAnyRule(rule_group: RuleGroup): boolean {
    for (let rule of rule_group.rules) {
      if (rule.is_assigned_to_user) {
        return true;
      }
    }
    return false;
  }

  isDisabled(rule: Rule) {
    // disable rule button if:
    // 1. not in edit mode
    // 2. rule is part of role: can only be deleted if role is deleted
    // 3. logged-in user does not have this role and is therefore not allowed to
    //    assign it
    if (
      !this.is_edit_mode ||
      rule.is_part_role ||
      !rule.is_assigned_to_loggedin
    ) {
      return true;
    }
    return false;
  }

  isDisabledScope(rule_group: RuleGroup): boolean {
    // disable a scope if
    // - not in edit mode
    // - the user already has all the rules in their roles that logged-in user
    //   is allowed to assign
    if (!this.is_edit_mode) {
      return true;
    }
    for (let rule of rule_group.rules) {
      if (
        (!rule.is_assigned_to_user && rule.is_assigned_to_loggedin) ||
        (!rule.is_part_role && rule.is_assigned_to_user)
      ) {
        return false;
      }
    }
    return true;
  }

  selectOrDeselect(rule: Rule): void {
    if (!rule.is_assigned_to_user) {
      this.added_rules.push(rule);
    } else {
      this.added_rules = removeMatchedIdFromArray(this.added_rules, rule);
    }
    rule.is_assigned_to_user = !rule.is_assigned_to_user;
    this.addedRulesChangeEvent.emit(this.added_rules);
  }

  selectOrDeselectScope(rule_group: RuleGroup): void {
    // check if the user already has all rules that may be assigned
    let has_all = this.userHasAllAssignableRules(rule_group);

    if (has_all) {
      // deselect rules in scope that are not part of a role
      for (let rule of rule_group.rules) {
        if (!rule.is_part_role) {
          this.selectOrDeselect(rule);
        }
      }
    } else {
      // select all remaining rules that can be assigned to the user
      for (let rule of rule_group.rules) {
        if (!rule.is_assigned_to_user && rule.is_assigned_to_loggedin) {
          this.selectOrDeselect(rule);
          rule.is_part_role = false;
        }
      }
    }
  }
}
