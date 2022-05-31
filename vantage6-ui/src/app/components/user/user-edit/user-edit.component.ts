import { Component, OnInit } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { OpsType, ResType } from 'src/app/shared/enum';
import { Rule } from 'src/app/interfaces/rule';
import { getEmptyUser, User } from 'src/app/interfaces/user';

import {
  getIdsFromArray,
  removeMatchedIdFromArray,
  removeMatchedIdsFromArray,
} from 'src/app/shared/utils';
import { ApiUserService } from 'src/app/services/api/api-user.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ActivatedRoute, Router } from '@angular/router';
import { UtilsService } from 'src/app/services/common/utils.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import { EMPTY_ORGANIZATION } from 'src/app/interfaces/organization';
import { take } from 'rxjs/operators';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';

// TODO add option to assign user to different organization?

@Component({
  selector: 'app-user-edit',
  templateUrl: './user-edit.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './user-edit.component.scss',
  ],
})
export class UserEditComponent implements OnInit {
  user: User = getEmptyUser();
  rules_all: Rule[] = [];
  roles_all: Role[] = [];
  roles_assignable_all: Role[] = [];
  roles_assignable: Role[] = [];
  loggedin_user: User = getEmptyUser();
  added_rules: Rule[] = [];
  can_assign_roles_rules: boolean = false;
  mode = OpsType.EDIT;
  organization_id: number = EMPTY_ORGANIZATION.id;

  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private userService: ApiUserService,
    private userDataService: UserDataService,
    private utilsService: UtilsService,
    private modalService: ModalService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    private convertJsonService: ConvertJsonService
  ) {}

  ngOnInit(): void {
    if (this.router.url.includes(OpsType.CREATE)) {
      this.mode = OpsType.CREATE;
    }
    this.userPermission.isInitialized().subscribe((ready) => {
      if (ready) {
        this.loggedin_user = this.userPermission.user;
        this.init();
      }
    });
  }

  async init() {
    // collect roles and rules (which is required to collect users)
    await this.setRules();
    await this.setRoles();

    // subscribe to id parameter in route to change edited user if required
    this.activatedRoute.paramMap.subscribe((params) => {
      let id = this.utilsService.getId(params, ResType.USER);
      if (this.mode === OpsType.CREATE) {
        this.organization_id = this.utilsService.getId(
          params,
          ResType.ORGANIZATION,
          'org_id'
        );
        this.setAssignableRoles();
      } else {
        this.setUser(id);
      }
    });
  }

  async setRules(): Promise<void> {
    (
      await this.ruleDataService.list(this.convertJsonService.getRole)
    ).subscribe((rules: Rule[]) => {
      this.rules_all = rules;
    });
  }

  async setRoles(): Promise<void> {
    (
      await this.roleDataService.list(this.convertJsonService.getRole, [
        this.rules_all,
      ])
    ).subscribe((roles: Role[]) => {
      this.roles_all = roles;
      this.setAssignableRoles();
    });
  }

  async setUser(id: number) {
    (
      await this.userDataService.get(id, this.convertJsonService.getUser, [
        this.roles_all,
        this.rules_all,
      ])
    ).subscribe((user: User) => {
      this.user = user;
      this.organization_id = this.user.organization_id;
      this.setAssignableRoles();
    });
  }

  async setAssignableRoles(): Promise<void> {
    if (this.roles_assignable_all.length === 0) {
      // if we are creating a new user, and there are no roles to assign, recheck
      // whether there are any roles to assign (they may be lost by page refresh)
      this.roles_assignable_all = await this.userPermission.getAssignableRoles(
        this.organization_id //TODO this is -1 when page refreshes!
      );
    }
    this.filterAssignableRoles();
    this.can_assign_roles_rules = this.userPermission.canModifyRulesOtherUser(
      this.user
    );
  }

  filterAssignableRoles(): void {
    /* remove all roles as 'assignable' that a user already has */
    let role_ids_user = getIdsFromArray(this.user.roles);
    this.roles_assignable = removeMatchedIdsFromArray(
      this.roles_assignable_all,
      role_ids_user
    );
  }

  removeRole(role: Role): void {
    this.user.roles = removeMatchedIdFromArray(this.user.roles, role.id);
    this.filterAssignableRoles();
  }
  removeRule(rule: Rule): void {
    this.user.rules = removeMatchedIdFromArray(this.user.rules, rule.id);
  }
  addRole(role: Role): void {
    // NB: new user roles are assigned using a spread operator to activate
    // angular change detection. This does not work with push()
    this.user.roles = [...this.user.roles, role];
    this.filterAssignableRoles();
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

    if (this.organization_id !== -1)
      this.user.organization_id = this.organization_id;

    let user_request;
    if (this.mode === OpsType.CREATE) {
      if (this.user.password !== this.user.password_repeated) {
        this.modalService.openMessageModal(ModalMessageComponent, [
          'Passwords do not match! Cannot create this user.',
        ]);
        return;
      }
      user_request = this.userService.create(this.user);
    } else {
      user_request = this.userService.update(this.user);
    }

    user_request.subscribe(
      (data) => {
        this.utilsService.goToPreviousPage();
      },
      (error) => {
        this.modalService.openMessageModal(ModalMessageComponent, [
          error.error.msg,
        ]);
      }
    );
  }

  cancelEdit(): void {
    this.utilsService.goToPreviousPage();
  }

  updateAddedRules($event: Rule[]) {
    this.added_rules = $event;
    this.user.rules = $event;
  }

  isCreate(): boolean {
    return this.mode === OpsType.CREATE;
  }
}
