import { Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';

import { EMPTY_USER, User } from '../interfaces/user';
import { EMPTY_ROLE, Role } from '../interfaces/role';
import { Rule } from '../interfaces/rule';
import { EMPTY_ORGANIZATION, Organization } from '../interfaces/organization';

import { UserPermissionService } from '../services/user-permission.service';
import { UserService } from '../services/api/user.service';
import { OrganizationService } from '../services/api/organization.service';
import { RoleService } from '../services/api/role.service';
import { parseId, removeMatchedIdFromArray } from '../utils';
import { ConvertJsonService } from '../services/convert-json.service';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { UserEditService } from '../user/user-edit.service';
import { RoleEditService } from '../role/role-edit.service';
import { RuleService } from '../services/api/rule.service';
import { ModalService } from '../modal/modal.service';
import { ModalMessageComponent } from '../modal/modal-message/modal-message.component';
import { OrganizationEditService } from './organization-edit.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['../globals/buttons.scss', './organization.component.scss'],
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
    private userService: UserService,
    private organizationService: OrganizationService,
    private roleService: RoleService,
    private convertJsonService: ConvertJsonService,
    private organizationEditService: OrganizationEditService,
    private userEditService: UserEditService,
    private roleEditService: RoleEditService,
    private ruleService: RuleService,
    private modalService: ModalService
  ) {}

  // TODO Now it is shown that there are no users/roles until they are loaded,
  // instead should say that they are being loaded
  ngOnInit(): void {
    this.init();
  }

  init(): void {
    // TODO this has a nested subscribe, fix that
    this.activatedRoute.paramMap.subscribe((params) => {
      let new_id = this._getId(params);
      if (new_id === EMPTY_ORGANIZATION.id) {
        return; // cannot get organization
      }
      if (new_id !== this.route_org_id) {
        this.route_org_id = new_id;
        this.userPermission.getUser().subscribe((user) => {
          this.loggedin_user = user;
          if (this.loggedin_user !== EMPTY_USER) {
            this.setup();
          }
        });
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

  private _getId(params: ParamMap): number {
    // get the organization id of the organization we're viewing
    let new_id = parseId(params.get('id'));
    if (isNaN(new_id)) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        "The organization id '" +
          params.get('id') +
          "' cannot be parsed. Please provide a valid organization id",
      ]);
      return EMPTY_ORGANIZATION.id;
    }
    return new_id;
  }

  async getOrganizationDetails(): Promise<void> {
    if (this.loggedin_user.organization_id === EMPTY_ORGANIZATION.id) return;

    // get data of organization that logged-in user is allowed to view
    let org_data = await this.organizationService.list().toPromise();

    // set organization data
    await this.setOrganizations(org_data);
  }

  async setOrganizations(organization_data: any) {
    this.organizations = [];
    for (let org of organization_data) {
      let new_org = this.convertJsonService.getOrganization(org);
      if (new_org.id === this.loggedin_user.organization_id) {
        // set organization of logged-in user as default current organization
        this.current_organization = new_org;
      }
      this.organizations.push(new_org);
    }
  }

  private _setCurrentOrganization(id: number): boolean {
    let current_org_found = false;
    for (let org of this.organizations) {
      if (org.id === id) {
        this.current_organization = org;
        current_org_found = true;
        break;
      }
    }
    return current_org_found;
  }

  async setCurrentOrganization(): Promise<void> {
    /* Renew the organization's users and roles */

    // set the current organization
    let current_org_found = this._setCurrentOrganization(this.route_org_id);
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
    let role_json = await this.roleService
      .list(this.route_org_id, true)
      .toPromise();
    this.setRoles(role_json);

    // collect users for current organization
    let user_json = await this.userService.list(this.route_org_id).toPromise();
    this.setUsers(user_json);
  }

  setRoles(role_data: any): void {
    this.roles = [];
    for (let role of role_data) {
      this.roles.push(this.convertJsonService.getRole(role, this.rules));
    }
    this.setRoleMetadata();
  }

  setRoleMetadata(): void {
    // set which roles currently logged in user can assign, and how many roles
    // are specific to the current organization
    this.roles_assignable = [];
    this.current_org_role_count = 0;
    for (let role of this.roles) {
      if (this.userPermission.canAssignRole(role)) {
        this.roles_assignable.push(role);
      }
      if (role.organization_id || this.current_organization.id === 1) {
        this.current_org_role_count += 1;
      }
    }
  }

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
    this.router.navigate(['/user/edit']);
  }

  editRole(role: Role): void {
    this.roleEditService.setRole(role);
    this.router.navigate(['/role/edit']);
  }

  createUser(): void {
    // initialize user
    let new_user: User = EMPTY_USER;
    new_user.organization_id = this.current_organization.id;
    new_user.is_being_created = true;

    // use edit mode to fill in all details of new user
    this.editUser(new_user);
  }

  createRole(): void {
    // initialize role
    let new_role: Role = EMPTY_ROLE;

    new_role.organization_id = this.current_organization.id;
    new_role.is_being_created = true;

    // use edit mode to fill in all details of new user
    this.editRole(new_role);
  }

  deleteUser(user: User): void {
    this.organization_users = removeMatchedIdFromArray(
      this.organization_users,
      user
    );
  }

  deleteRole(role: Role): void {
    // remove role
    this.roles = removeMatchedIdFromArray(this.roles, role);
    // set data on which roles user can assign, how many roles there are for
    // the current organization
    this.setRoleMetadata();
    // delete this role from any user it was assigned to (this is also done
    // separately in the backend)
    this.deleteRoleFromUsers(role);
  }

  private deleteRoleFromUsers(role: Role): void {
    for (let user of this.organization_users) {
      user.roles = removeMatchedIdFromArray(user.roles, role);
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
