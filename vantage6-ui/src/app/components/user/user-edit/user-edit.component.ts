import { Component, OnInit } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { OpsType, ResType } from 'src/app/shared/enum';
import { Rule } from 'src/app/interfaces/rule';
import { getEmptyUser, User } from 'src/app/interfaces/user';

import {
  deepcopy,
  getIdsFromArray,
  parseId,
  removeMatchedIdFromArray,
  removeMatchedIdsFromArray,
} from 'src/app/shared/utils';
import { ApiUserService } from 'src/app/services/api/api-user.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ActivatedRoute, Router } from '@angular/router';
import { UtilsService } from 'src/app/services/common/utils.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import {
  EMPTY_ORGANIZATION,
  Organization,
} from 'src/app/interfaces/organization';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';

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
  organizations: Organization[] = [];
  selected_org: Organization | null = null;
  route_id: number | null = null;

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
    private orgDataService: OrgDataService
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
      if (this.mode === OpsType.CREATE) {
        this.route_id = parseId(params.get('org_id'));
        this.organization_id = this.route_id;
        this.setupCreateUser();
      } else {
        let id = this.utilsService.getId(params, ResType.USER);
        this.setUser(id);
      }
    });
  }

  async setupCreateUser() {
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

  async setRoles(): Promise<void> {
    (await this.roleDataService.list(this.rules_all)).subscribe(
      (roles: Role[]) => {
        this.roles_all = roles;
        this.setAssignableRoles();
      }
    );
  }

  async setUser(id: number) {
    this.user = await this.userDataService.get(
      id,
      this.roles_all,
      this.rules_all
    );
    this.organization_id = this.user.organization_id;
    this.setAssignableRoles();
  }

  async setAssignableRoles(): Promise<void> {
    if (
      (this.roles_assignable_all.length === 0 &&
        this.organization_id !== EMPTY_ORGANIZATION.id) ||
      !this.rolesMatchOrgId()
    ) {
      // first get all roles assignable for the organization this user is in
      this.roles_assignable_all = deepcopy(
        await this.roleDataService.org_list(
          this.organization_id,
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
      if (
        role.organization_id !== null &&
        role.organization_id !== this.organization_id
      )
        return false;
    }
    return true;
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
        if (this.mode === OpsType.CREATE) {
          // save user is to data service (so it is displayed everywhere)
          this.user.id = data.id;
          this.userDataService.save(this.user);
        }
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

  getTextReasonNoRoles(): string {
    if (!this.can_assign_roles_rules) {
      return "You cannot change the permissions of this user because they have permissions you don't have.";
    } else if (this.isCreateAnyOrg()) {
      return 'Please select an organization first to determine which roles are available.';
    } else {
      return 'There are no roles left that you can assign to this user.';
    }
  }

  isCreateAnyOrg(): boolean {
    return this.isCreate() && !this.route_id && this.selected_org === null;
  }

  selectOrg(org: Organization): void {
    this.selected_org = org;
    this.organization_id = org.id;
    this.setAssignableRoles();
  }

  getNameOrgDropdown(): string {
    return this.selected_org === null
      ? 'Select organization'
      : this.selected_org.name;
  }
}
