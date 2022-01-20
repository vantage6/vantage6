import { Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';

import { EMPTY_USER, User } from '../interfaces/user';
import { EMPTY_ROLE, Role } from '../interfaces/role';
import { Rule } from '../interfaces/rule';
import { EMPTY_ORGANIZATION, Organization } from '../interfaces/organization';

import { UserPermissionService } from '../services/user-permission.service';
import { UserService } from '../services/api/user.service';
import { OrganizationService } from '../services/api/organization.service';
import { ModalService } from '../services/modal.service';
import { RoleService } from '../services/api/role.service';
import { deepcopy, getById, removeMatchedIdFromArray } from '../utils';
import { ChangeExit } from '../globals/enum';
import { ConvertJsonService } from '../services/convert-json.service';
import { Router } from '@angular/router';
import { UserEditService } from '../user/user-edit.service';
import { RoleEditService } from '../role/role-edit.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['./organization.component.scss'],
})
export class OrganizationComponent implements OnInit {
  organizations: Organization[] = [];
  current_organization: Organization = EMPTY_ORGANIZATION;
  loggedin_user_organization_id: number = -1;
  loggedin_user: User = EMPTY_USER;
  organization_users: User[] = [];
  roles: Role[] = [];
  roles_assignable: Role[] = [];
  current_org_role_count: number = 0;
  all_rules: Rule[] = [];

  constructor(
    private router: Router,
    public userPermission: UserPermissionService,
    private userService: UserService,
    private organizationService: OrganizationService,
    private roleService: RoleService,
    private convertJsonService: ConvertJsonService,
    private userEditService: UserEditService,
    private roleEditService: RoleEditService
  ) {}

  // TODO Now it is shown that there are no users/roles until they are loaded,
  // instead should say that they are being loaded
  ngOnInit(): void {
    this.userPermission.getUser().subscribe((user) => {
      this.loggedin_user = user;
      this.getOrganizationDetails();
    });
    this.userPermission.getRuleDescriptions().subscribe((rules) => {
      this.all_rules = rules;
    });
  }

  getOrganizationDetails(): void {
    if (
      this.loggedin_user.id === EMPTY_USER.id ||
      !this.userPermission.hasPermission('view', 'organization', '*')
    )
      return;

    // get user data
    //TODO this request is done here for the second time (first time in userPermission). Improve efficiency
    let req_user = this.userService.get(this.loggedin_user.id);

    // get organization data
    let req_organizations = this.organizationService.list();

    // first obtain user information to get organization id, then obtain
    // organization information
    forkJoin([req_user, req_organizations]).subscribe(
      (data: any) => {
        let current_user_data = data[0];
        let organization_data = data[1];
        this.loggedin_user_organization_id = current_user_data.organization.id;
        this.setOrganizations(organization_data);

        this.collectUserAndRoles();
      },
      (error) => {
        console.log(error);
      }
    );
  }

  selectOrganizationDropdown(org_id: number): void {
    for (let org of this.organizations) {
      if (org.id === org_id) {
        this.current_organization = org;
        break;
      }
    }
    this.collectUserAndRoles();
  }

  setOrganizations(organization_data: any[]) {
    for (let org of organization_data) {
      let new_org = this.getOrgObject(org);
      if (new_org.id === this.loggedin_user_organization_id) {
        // set organization of logged-in user as default current organization
        this.current_organization = new_org;
      }
      this.organizations.push(new_org);
    }
  }

  getOrgObject(org_object: any): Organization {
    return {
      id: org_object.id,
      name: org_object.name,
      address1: org_object.address1,
      address2: org_object.address2,
      zipcode: org_object.zipcode,
      country: org_object.country,
      domain: org_object.domain,
      public_key: org_object.public_key,
    };
  }

  collectUserAndRoles(): void {
    /* Renew the organization's users and roles */
    if (this.current_organization === null) {
      return;
    }
    this.organization_users = [];

    // collect users for current organization
    let req_users = this.userService.list(this.current_organization.id);

    // collect roles for current organization
    let req_roles = this.roleService.list(this.current_organization.id, true);

    // join users, roles and rules requests to set organization page variables
    forkJoin([req_users, req_roles]).subscribe(
      (data: any) => {
        // set roles
        this.setRoles(data[1]);

        // set users
        this.setUsers(data[0]);
      },
      (error) => {
        console.log(error);
      }
    );
  }

  setRoles(role_data: any[]): void {
    this.roles = [];
    this.roles_assignable = [];
    this.current_org_role_count = 0;
    for (let role of role_data) {
      this.roles.push(this.convertJsonService.getRole(role, this.all_rules));
      if (role.organization || this.current_organization.id === 1) {
        this.current_org_role_count += 1;
      }
    }
    // set which roles currently logged in user can assign
    for (let role of this.roles) {
      if (this.userPermission.canAssignRole(role)) {
        this.roles_assignable.push(role);
      }
    }
  }

  setUsers(user_data: any[]): void {
    for (let user_json of user_data) {
      let user = this.convertJsonService.getUser(
        user_json,
        this.roles,
        this.all_rules
      );
      user.is_logged_in = user.id === this.loggedin_user.id;
      this.organization_users.push(user);
    }
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
    // TODO add: are you sure?
    this.organization_users = removeMatchedIdFromArray(
      this.organization_users,
      user
    );
  }

  endRoleEditing($event: ChangeExit, role: Role, role_idx: number) {}

  addNewlyCreatedRole(id: number, role: Role): void {}

  deleteRole(role: Role): void {}

  cancelNewRole(is_remove_new_role: boolean): void {}
}
