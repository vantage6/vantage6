import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { User } from 'src/app/interfaces/user';

import { removeMatchedIdFromArray } from 'src/app/utils';
import { UserService } from 'src/app/services/api/user.service';
import { UserPermissionService } from 'src/app/services/user-permission.service';
import { ChangeExit } from 'src/app/globals/enum';

// TODO add option to assign user to different organization

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
    organization_id: -1,
    roles: [],
    rules: [],
  };
  @Input() roles_assignable: Role[] = [];
  @Output() finishedEditing = new EventEmitter<ChangeExit>();
  @Output() cancelNewUser = new EventEmitter<boolean>();
  userId: number = 0;
  added_rules: Rule[] = [];

  constructor(
    public userPermission: UserPermissionService,
    private userService: UserService
  ) {}

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

  getRulesNotInRoles(): Rule[] {
    let rules_not_in_roles: Rule[] = [];
    for (let rule of this.added_rules) {
      if (!rule.is_part_role) {
        rules_not_in_roles.push(rule);
      }
    }
    return rules_not_in_roles;
  }

  saveEditedUser(user: User): void {
    user.rules = this.getRulesNotInRoles();

    let user_request;
    if (user.is_being_created) {
      if (user.password !== user.password_repeated) {
        alert('Passwords do not match! Cannot create this user.');
        return;
      }
      user_request = this.userService.create(user);
    } else {
      user_request = this.userService.update(user);
    }

    user_request.subscribe(
      (data) => {
        this.finishedEditing.emit(ChangeExit.SAVE);
        console.log(data);
      },
      (error) => {
        alert(error.error.msg);
      }
    );
  }

  cancelEdit(): void {
    if (this.user.is_being_created) {
      this.cancelNewUser.emit(true);
    }
    this.finishedEditing.emit(ChangeExit.CANCEL);
  }

  updateAddedRules($event: Rule[]) {
    this.added_rules = $event;
    this.user.rules = $event;
  }
}
