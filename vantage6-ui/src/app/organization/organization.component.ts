import { Component, OnInit } from '@angular/core';

import { EMPTY_USER, getEmptyUser, User } from 'src/app/user/interfaces/user';
import { getEmptyRole, Role } from 'src/app/role/interfaces/role';
import { Rule } from 'src/app/rule/interfaces/rule';
import { EMPTY_ORGANIZATION, Organization } from './interfaces/organization';
import { Resource } from '../shared/enum';
import {
  arrayContainsObjWithId,
  getById,
  removeMatchedIdFromArray,
} from 'src/app/shared/utils';

import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ApiUserService } from 'src/app/user/services/api-user.service';
import { ApiOrganizationService } from './services/api-organization.service';
import { ApiRoleService } from 'src/app/role/services/api-role.service';
import { ConvertJsonService } from 'src/app/shared/services/convert-json.service';
import { ActivatedRoute, Router } from '@angular/router';
import { UserEditService } from 'src/app/user/services/user-edit.service';
import { RoleEditService } from 'src/app/role/services/role-edit.service';
import { ApiRuleService } from 'src/app/rule/services/api-rule.service';
import { ModalService } from '../modal/modal.service';
import { ModalMessageComponent } from '../modal/modal-message/modal-message.component';
import { OrganizationEditService } from './services/organization-edit.service';
import { UtilsService } from '../shared/services/utils.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['../shared/scss/buttons.scss', './organization.component.scss'],
})
export class OrganizationComponent implements OnInit {
  organizations: Organization[] = [];
  route_org_id: number = EMPTY_ORGANIZATION.id;
  current_organization: Organization = EMPTY_ORGANIZATION;
  loggedin_user: User = EMPTY_USER;
  organization_users: User[] = [];
  roles: Role[] = [];
  roles_assignable: Role[] = [];
  current_org_role_count: number = 0;
  rules: Rule[] = [];

  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private userService: ApiUserService,
    private organizationService: ApiOrganizationService,
    private roleService: ApiRoleService,
    private convertJsonService: ConvertJsonService,
    private organizationEditService: OrganizationEditService,
    private userEditService: UserEditService,
    private roleEditService: RoleEditService,
    private ruleService: ApiRuleService,
    private modalService: ModalService,
    private utilsService: UtilsService
  ) {}

  // TODO Now it is shown that there are no users/roles until they are loaded,
  // instead should say that they are being loaded
  ngOnInit(): void {
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) this.init();
    });
  }

  init(): void {
    // TODO this has a nested subscribe, fix that
    this.activatedRoute.paramMap.subscribe((params) => {
      let new_id = this.utilsService.getId(params, Resource.ORGANIZATION);
      if (new_id === EMPTY_ORGANIZATION.id) {
        return; // cannot get organization
      }
      if (new_id !== this.route_org_id) {
        this.route_org_id = new_id;
        this.loggedin_user = this.userPermission.user;
        if (this.loggedin_user !== EMPTY_USER) {
          this.setup();
        }
      }
    });
    this.ruleService.getRules().subscribe((rules) => {
      this.rules = rules;
    });
  }

  async setup() {
    // get all organizations that the user is allowed to see
    await this.getOrganizationDetails();

    // set the currently requested organization's users/roles/etc
    this.setCurrentOrganization();
  }

  async getOrganizationDetails(): Promise<void> {
    if (this.loggedin_user.organization_id === EMPTY_ORGANIZATION.id) return;

    // get data of organization that logged-in user is allowed to view
    this.organizations = await this.organizationService.getOrganizations();

    // set current organization
    this.current_organization = getById(this.organizations, this.route_org_id);
  }

  private _allowedToSeeOrg(id: number): boolean {
    /* returns true if organizaiton with certain id exists and the logged-in
       user is allowed to see it */
    return arrayContainsObjWithId(id, this.organizations);
  }

  async setCurrentOrganization(): Promise<void> {
    /* Renew the organization's users and roles */

    // set the current organization
    let current_org_found = this._allowedToSeeOrg(this.route_org_id);
    if (!current_org_found) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        "Could not show data on organization with id '" +
          this.route_org_id +
          "'",
        'Showing data on your own organization instead!',
      ]);
      this.router.navigate([
        'organization',
        this.loggedin_user.organization_id,
      ]);
    }

    // first collect roles for current organization. This is done before
    // collecting the users so that the users can possess these roles
    this.roles = await this.roleService.getOrganizationRoles(
      this.current_organization.id
    );
    this.roles_assignable = await this.userPermission.getAssignableRoles(
      this.current_organization.id,
      this.roles
    );
    this.setRoleMetadata();

    // collect users for current organization
    let user_json = await this.userService.list(this.route_org_id).toPromise();
    this.setUsers(user_json);
  }

  setRoleMetadata(): void {
    // set how many roles are specific to the current organization
    this.current_org_role_count = 0;
    for (let role of this.roles) {
      if (role.organization_id || this.current_organization.id === 1) {
        this.current_org_role_count += 1;
      }
    }
  }

  // TODO via API user service?!
  setUsers(user_data: any): void {
    this.organization_users = [];
    for (let user_json of user_data) {
      let user = this.convertJsonService.getUser(
        user_json,
        this.roles,
        this.rules
      );
      user.is_logged_in = user.id === this.loggedin_user.id;
      this.organization_users.push(user);
    }
  }

  editOrganization(org: Organization): void {
    this.organizationEditService.setOrganization(org);
  }

  editUser(user: User): void {
    this.userEditService.set(user, this.roles_assignable);
  }

  createUser(): void {
    this.userEditService.set(getEmptyUser(), this.roles_assignable);
  }

  deleteUser(user: User): void {
    this.organization_users = removeMatchedIdFromArray(
      this.organization_users,
      user.id
    );
  }

  createRole(): void {
    // initialize role
    let new_role: Role = getEmptyRole();
    new_role.organization_id = this.current_organization.id;

    // use edit mode to fill in all details of new user
    this.roleEditService.setRole(new_role);
  }

  async deleteRole(role: Role): Promise<void> {
    // remove role
    this.roles = removeMatchedIdFromArray(this.roles, role.id);
    // set data on which roles user can assign, how many roles there are for
    // the current organization
    this.roles_assignable = await this.userPermission.getAssignableRoles(
      this.current_organization.id,
      this.roles
    );
    this.setRoleMetadata();
    // delete this role from any user it was assigned to (this is also done
    // separately in the backend)
    this.deleteRoleFromUsers(role);
  }

  private deleteRoleFromUsers(role: Role): void {
    for (let user of this.organization_users) {
      user.roles = removeMatchedIdFromArray(user.roles, role.id);
    }
  }

  showPublicKey(): void {
    this.modalService.openMessageModal(ModalMessageComponent, [
      'The public key is:',
      this.current_organization.public_key,
    ]);
    // TODO add functionality to modify the public key
  }
}
