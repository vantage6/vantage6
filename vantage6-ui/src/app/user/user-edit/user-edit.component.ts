import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { EMPTY_USER, User } from 'src/app/interfaces/user';

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
  @Output() newlyCreatedUserId = new EventEmitter<number>();
  loggedin_user: User = EMPTY_USER;
  added_rules: Rule[] = [];

  constructor(
    public userPermission: UserPermissionService,
    private userService: UserService
  ) {}

  ngOnInit(): void {
    this.userPermission.getUser().subscribe((user) => {
      this.loggedin_user = user;
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
        this.user.is_being_edited = false;
        this.finishedEditing.emit(ChangeExit.SAVE);
        if (this.user.is_being_created) {
          this.newlyCreatedUserId.emit(data.id);
        }
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
    this.user.is_being_edited = false;
    this.finishedEditing.emit(ChangeExit.CANCEL);
  }

  updateAddedRules($event: Rule[]) {
    this.added_rules = $event;
    this.user.rules = $event;
  }
}
