import { Component, OnInit } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { getEmptyUser, User } from 'src/app/interfaces/user';
import { OpsType } from 'src/app/shared/enum';

import { ActivatedRoute, Router } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import { Organization } from 'src/app/interfaces/organization';
import { UserApiService } from 'src/app/services/api/user-api.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { UtilsService } from 'src/app/services/common/utils.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import {
  deepcopy,
  getIdsFromArray,
  removeMatchedIdFromArray,
  removeMatchedIdsFromArray,
} from 'src/app/shared/utils';
import { BaseEditComponent } from '../../base/base-edit/base-edit.component';

// TODO add option to assign user to different organization?

@Component({
  selector: 'app-user-edit',
  templateUrl: './user-edit.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './user-edit.component.scss',
  ],
})
export class UserEditComponent extends BaseEditComponent implements OnInit {
  loggedin_user: User = getEmptyUser();
  user: User = getEmptyUser();
  user_orig_name: string = '';
  rules_all: Rule[] = [];
  roles_all: Role[] = [];
  roles_assignable_all: Role[] = [];
  roles_assignable: Role[] = [];

  added_rules: Rule[] = [];
  can_assign_roles_rules: boolean = false;

  constructor(
    protected router: Router,
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    protected userApiService: UserApiService,
    protected userDataService: UserDataService,
    protected utilsService: UtilsService,
    protected modalService: ModalService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    private orgDataService: OrgDataService
  ) {
    super(
      router,
      activatedRoute,
      userPermission,
      utilsService,
      userApiService,
      userDataService,
      modalService
    );
  }

  async init() {
    this.loggedin_user = this.userPermission.user;

    // collect roles and rules (which is required to collect users)
    await this.setRules();
    await this.setRoles();

    // subscribe to id/org_id parameter in route
    this.readRoute();
  }

  async setupCreate() {
    if (!this.organization_id) {
      (await this.orgDataService.list()).subscribe((orgs: Organization[]) => {
        this.organizations = orgs;
      });
    } else {
      this.setAssignableRoles();
    }
  }

  async setRules(): Promise<void> {
    (await this.ruleDataService.list()).subscribe((rules: Rule[]) => {
      this.rules_all = rules;
    });
  }

  // TODO get only roles from the relevant organization
  async setRoles(): Promise<void> {
    (await this.roleDataService.list(this.rules_all)).subscribe(
      (roles: Role[]) => {
        this.roles_all = roles;
        this.setAssignableRoles();
      }
    );
  }

  async setupEdit(id: number) {
    let user = await this.userDataService.get(
      id,
      this.roles_all,
      this.rules_all
    );
    if (user) {
      this.user = user;
      this.user_orig_name = this.user.username;
      this.organization_id = this.user.organization_id;
      this.setAssignableRoles();
    }
  }

  async setAssignableRoles(): Promise<void> {
    if (
      (this.roles_assignable_all.length === 0 && this.organization_id) ||
      !this.rolesMatchOrgId()
    ) {
      // first get all roles assignable for the organization this user is in
      this.roles_assignable_all = deepcopy(
        await this.roleDataService.org_list(
          this.organization_id as number,
          this.rules_all
        )
      );
      // if we are creating a new user, and there are no roles to assign, recheck
      // whether there are any roles to assign (they may be lost by page refresh)
      this.roles_assignable_all = await this.userPermission.getAssignableRoles(
        this.roles_assignable_all
      );
    }
    this.filterAssignableRoles();
    this.can_assign_roles_rules = this.userPermission.canModifyRulesOtherUser(
      this.user
    );
  }

  rolesMatchOrgId(): boolean {
    for (let role of this.roles_assignable_all) {
      if (role.organization_id === this.organization_id) return true;
    }
    return false;
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

  async save(): Promise<void> {
    this.user.rules = this.getRulesNotInRoles();

    if (this.organization_id) this.user.organization_id = this.organization_id;

    if (
      this.mode === OpsType.CREATE &&
      this.user.password !== this.user.password_repeated
    ) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'Passwords do not match! Cannot create this user.',
      ]);
      return;
    }

    super.save(this.user);
  }

  updateAddedRules($event: Rule[]) {
    this.added_rules = $event;
    this.user.rules = $event;
  }

  getTextReasonNoRoles(): string {
    if (!this.can_assign_roles_rules) {
      return "You cannot change the permissions of this user because they have permissions you don't have.";
    } else if (this.isCreateAnyOrg()) {
      return 'Please select an organization first to determine which roles are available.';
    } else {
      return 'There are no roles left that you can assign to this user.';
    }
  }

  selectOrg(org: Organization): void {
    super.selectOrg(org);
    // remove any roles from the user that are only applicable to another
    // organization
    this.user.roles = this.user.roles.filter((role) => {
      return role.organization_id === null || role.organization_id === org.id;
    });
    // set assignable roles for this organization
    this.setAssignableRoles();
  }

  getTitle(): string {
    return this.mode === OpsType.EDIT
      ? `Edit user '${this.user_orig_name}'`
      : 'Create a new user';
  }
}
