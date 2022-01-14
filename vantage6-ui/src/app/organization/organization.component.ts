import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';

import { User } from '../interfaces/user';
import { Role } from '../interfaces/role';
import { Rule } from '../interfaces/rule';
import { Organization } from '../interfaces/organization';

import { UserPermissionService } from '../services/user-permission.service';
import { UserService } from '../services/api/user.service';
import { OrganizationService } from '../services/api/organization.service';
import { ModalService } from '../services/modal.service';
import { RoleService } from '../services/api/role.service';
import { deepcopy, removeMatchedIdFromArray } from '../utils';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['./organization.component.scss'],
})
export class OrganizationComponent implements OnInit {
  organizations: Organization[] = [];
  current_organization: Organization = {
    id: -1,
    name: '',
    address1: '',
    address2: '',
    zipcode: '',
    country: '',
    domain: '',
    public_key: '',
  };
  user_organization_id: number = -1;
  organization_users: User[] = [];
  roles: Role[] = [];
  current_org_role_count: number = 0;
  all_rules: Rule[] = [];
  users_edit_originals: User[] = [];
  userId: number = 0;

  constructor(
    public userPermission: UserPermissionService,
    private userService: UserService,
    private organizationService: OrganizationService,
    private roleService: RoleService,
    private router: Router
  ) {}

  // TODO Now it is shown that there are no users/roles until they are loaded,
  // instead should say that they are being loaded
  ngOnInit(): void {
    this.userPermission.getUserId().subscribe((id) => {
      this.userId = id;
      this.getOrganizationDetails();
    });
    this.userPermission.getRuleDescriptions().subscribe((rules) => {
      this.all_rules = rules;
    });
  }

  getOrganizationDetails(): void {
    if (this.userId === 0) return;

    // get user data
    let req_user = this.userService.get(this.userId);

    // get organization data
    let req_organizations = this.organizationService.list();

    // first obtain user information to get organization id, then obtain
    // organization information
    forkJoin([req_user, req_organizations]).subscribe(
      (data: any) => {
        let current_user_data = data[0];
        let organization_data = data[1];
        this.user_organization_id = current_user_data.organization.id;
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
      if (new_org.id === this.user_organization_id) {
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
    this.users_edit_originals = [];

    // collect users for current organization
    let req_users = this.userService.list(this.current_organization.id);

    // collect roles for current organization
    let req_roles = this.roleService.list(this.current_organization.id, true);

    // join users, roles and rules requests to set organization page variables
    forkJoin([req_users, req_roles]).subscribe(
      (data: any) => {
        let users = data[0];
        this.roles = [];
        this.current_org_role_count = 0;
        for (let role of data[1]) {
          let rules: Rule[] = [];
          for (let rule of role.rules) {
            rules.push(this._getDescription(rule.id, this.all_rules));
          }
          this.roles.push({
            id: role.id,
            name: role.name,
            description: role.description,
            organization_id: role.organization ? role.organization.id : null,
            rules: rules,
          });
          if (role.organization || this.current_organization.id === 1) {
            this.current_org_role_count += 1;
          }
        }
        for (let user of users) {
          let user_roles: Role[] = [];
          if (user.roles) {
            user.roles.forEach((role: any) => {
              let r = this._getDescription(role.id, this.roles);
              if (r !== undefined) {
                user_roles.push(r);
              }
            });
          }
          let user_rules: Rule[] = [];
          if (user.rules) {
            user.rules.forEach((rule: any) => {
              let r = this._getDescription(rule.id, this.all_rules);
              user_rules.push(r);
            });
          }
          this.organization_users.push({
            id: user.id,
            username: user.username,
            first_name: user.firstname,
            last_name: user.lastname,
            email: user.email,
            roles: user_roles,
            rules: user_rules,
          });
        }
      },
      (error) => {
        console.log(error);
      }
    );
  }

  editUser(user: User): void {
    this.users_edit_originals.push(deepcopy(user));
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

  isUserBeingEdited(user_id: number) {
    return this.users_edit_originals.some((u) => u.id === user_id);
  }

  createUser(): void {
    this.router.navigate(['user/create']);
  }

  private _getDescription(id: number, descriptions: any[]) {
    for (let d of descriptions) {
      if (d.id === id) {
        return d;
      }
    }
  }
}
