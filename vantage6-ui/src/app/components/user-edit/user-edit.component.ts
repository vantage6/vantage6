import { Component, Input, OnInit } from '@angular/core';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';

import { User } from 'src/app/interfaces/user';

import { UserPermissionService } from 'src/app/services/user-permission.service';
import { removeMatchedIdFromArray } from 'src/app/utils';

@Component({
  selector: 'app-user-edit',
  templateUrl: './user-edit.component.html',
  styleUrls: ['./user-edit.component.scss'],
})
export class UserEditComponent implements OnInit {
  @Input() user: User = {
    id: -1,
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    roles: [],
    rules: [],
  };
  @Input() roles_assignable: Role[] = [];
  userId: number = 0;

  constructor(public userPermission: UserPermissionService) {}

  ngOnInit(): void {
    this.userPermission.getUserId().subscribe((id) => {
      this.userId = id;
    });
  }

  removeRole(user: User, role: Role): void {
    user.roles = removeMatchedIdFromArray(user.roles, role);
  }
  removeRule(user: User, rule: Rule): void {
    user.rules = removeMatchedIdFromArray(user.rules, rule);
  }
  addRole(user: User, role: Role): void {
    // NB: new user roles are assigned using a spread operator to activate
    // angular change detection. This does not work with push()
    user.roles = [...user.roles, role];
  }
  addRule(user: User, rule: Rule): void {
    // NB: new user roles are assigned using a spread operator to activate
    // angular change detection. This does not work with push()
    user.rules = [...user.rules, rule];
  }

  saveEditedUser(
    user: User
    // editedPermissions: PermissionTableComponent
  ): void {
    // user.rules = editedPermissions.getRulesNotInRoles();
  }
}
