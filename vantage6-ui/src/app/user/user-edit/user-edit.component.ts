import { Component, OnInit } from '@angular/core';
import { Location } from '@angular/common';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { EMPTY_USER, User } from 'src/app/interfaces/user';

import { removeMatchedIdFromArray } from 'src/app/utils';
import { UserService } from 'src/app/services/api/user.service';
import { UserPermissionService } from 'src/app/services/user-permission.service';
import { UserEditService } from '../user-edit.service';

// TODO add option to assign user to different organization

@Component({
  selector: 'app-user-edit',
  templateUrl: './user-edit.component.html',
  styleUrls: ['./user-edit.component.scss'],
})
export class UserEditComponent implements OnInit {
  user: User = EMPTY_USER;
  roles_assignable: Role[] = [];
  loggedin_user: User = EMPTY_USER;
  added_rules: Rule[] = [];

  constructor(
    private location: Location,
    public userPermission: UserPermissionService,
    private userService: UserService,
    private userEditService: UserEditService
  ) {}

  ngOnInit(): void {
    this.userPermission.getUser().subscribe((user) => {
      this.loggedin_user = user;
    });
    this.userEditService.getUser().subscribe((user) => {
      this.user = user;
    });
    this.userEditService.getAvailableRoles().subscribe((roles) => {
      this.roles_assignable = roles;
    });
  }

  removeRole(role: Role): void {
    this.user.roles = removeMatchedIdFromArray(this.user.roles, role);
  }
  removeRule(rule: Rule): void {
    this.user.rules = removeMatchedIdFromArray(this.user.rules, rule);
  }
  addRole(role: Role): void {
    // NB: new user roles are assigned using a spread operator to activate
    // angular change detection. This does not work with push()
    this.user.roles = [...this.user.roles, role];
  }
  addRule(rule: Rule): void {
    // NB: new user roles are assigned using a spread operator to activate
    // angular change detection. This does not work with push()
    this.user.rules = [...this.user.rules, rule];
  }

  getRulesNotInRoles(): Rule[] {
    let rules_not_in_roles: Rule[] = [];
    for (let rule of this.added_rules) {
      if (!rule.is_part_role) {
        rules_not_in_roles.push(rule);
      }
    }
    return rules_not_in_roles;
  }

  saveEditedUser(): void {
    this.user.rules = this.getRulesNotInRoles();

    let user_request;
    if (this.user.is_being_created) {
      if (this.user.password !== this.user.password_repeated) {
        alert('Passwords do not match! Cannot create this user.');
        return;
      }
      user_request = this.userService.create(this.user);
    } else {
      user_request = this.userService.update(this.user);
    }

    user_request.subscribe(
      (data) => {
        this.goBack();
      },
      (error) => {
        alert(error.error.msg);
      }
    );
  }

  cancelEdit(): void {
    this.goBack();
  }

  updateAddedRules($event: Rule[]) {
    this.added_rules = $event;
    this.user.rules = $event;
  }

  goBack(): void {
    // go back to previous page
    this.location.back();
  }
}
