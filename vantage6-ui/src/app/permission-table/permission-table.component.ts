import { Component, Input, OnChanges, OnInit } from '@angular/core';

import { Role } from '../interfaces/role';
import { Rule } from '../interfaces/rule';

import { UserPermissionService } from '../services/user-permission.service';

@Component({
  selector: 'app-permission-table',
  templateUrl: './permission-table.component.html',
  styleUrls: ['./permission-table.component.scss'],
})
// , OnChanges
export class PermissionTableComponent implements OnInit {
  @Input() given_roles: Role[] = [];
  @Input() given_rules: Rule[] = [];
  @Input() is_edit_mode: boolean = false;
  user_rules: Rule[] = [];

  constructor(public userPermission: UserPermissionService) {}

  ngOnInit(): void {
    this.setUserRules();
  }

  // ngOnChanges(): void {
  //    setUserRules()
  // }

  setUserRules(): void {
    for (let role of this.given_roles) {
      this.user_rules.push(...role.rules);
    }
    this.user_rules.push(...this.given_rules);

    // remove double rules
    this.user_rules = [...new Set(this.user_rules)];
  }

  getClass(type: string, resource: string, scope: string) {
    const user_has = this.userPermission.getPermissionSubset(
      this.user_rules,
      type,
      resource,
      scope
    );
    if (user_has.length > 0) {
      return 'btn btn-has-permission';
    } else {
      return 'btn btn-no-permission';
    }
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
    if (user_has.length === available_rules.length) {
      return 'btn btn-has-permission';
    } else if (user_has.length > 0) {
      return 'btn btn-part-permission';
    } else {
      return 'btn btn-no-permission';
    }
  }

  isDisabled() {
    if (!this.is_edit_mode) {
      return true;
    }
    return false;
  }
}
