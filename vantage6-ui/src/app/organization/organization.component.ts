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
import { removeMatchedIdFromArray } from '../utils';
import { ConvertJsonService } from '../services/convert-json.service';
import { Router } from '@angular/router';
import { UserEditService } from '../user/user-edit.service';
import { RoleEditService } from '../role/role-edit.service';
import { RuleService } from '../services/api/rule.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['./organization.component.scss'],
})
export class OrganizationComponent implements OnInit {
  organizations: Organization[] = [];
  current_organization: Organization = EMPTY_ORGANIZATION;
  loggedin_user: User = EMPTY_USER;
  organization_users: User[] = [];
  roles: Role[] = [];
  roles_assignable: Role[] = [];
  current_org_role_count: number = 0;
  rules: Rule[] = [];

  constructor(
    private router: Router,
    public userPermission: UserPermissionService,
    private userService: UserService,
    private organizationService: OrganizationService,
    private roleService: RoleService,
    private convertJsonService: ConvertJsonService,
    private userEditService: UserEditService,
    private roleEditService: RoleEditService,
    private ruleService: RuleService
  ) {}

  // TODO Now it is shown that there are no users/roles until they are loaded,
  // instead should say that they are being loaded
  ngOnInit(): void {
    this.userPermission.getUser().subscribe((user) => {
      this.loggedin_user = user;
      this.getOrganizationDetails();
    });
    this.ruleService.getRules().subscribe((rules) => {
      this.rules = rules;
    });
  }

  getOrganizationDetails(): void {
    if (
      this.loggedin_user.id === EMPTY_USER.id ||
      !this.userPermission.hasPermission('view', 'organization', '*')
    )
      return;

    // first obtain user information to get organization id, then obtain
    // organization information
    this.organizationService.list().subscribe(
      (organization_data: any) => {
        this.setOrganizations(organization_data);
        this.collectUsersAndRoles();
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
    this.collectUsersAndRoles();
  }

  setOrganizations(organization_data: any[]) {
    for (let org of organization_data) {
      let new_org = this.getOrgObject(org);
      if (new_org.id === this.loggedin_user.organization_id) {
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

  async collectUsersAndRoles(): Promise<void> {
    /* Renew the organization's users and roles */
    if (this.current_organization === null) {
      return;
    }
    this.organization_users = [];

    // first collect roles for current organization. This is done before
    // collecting the users so that the users can possess these roles
    let role_json = await this.roleService
      .list(this.current_organization.id, true)
      .toPromise();
    this.setRoles(role_json);

    // collect users for current organization
    let user_json = await this.userService
      .list(this.current_organization.id)
      .toPromise();
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
}
