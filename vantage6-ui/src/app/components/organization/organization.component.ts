import { Component, OnInit } from '@angular/core';

import { EMPTY_USER, getEmptyUser, User } from 'src/app/interfaces/user';
import { getEmptyRole, Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import {
  EMPTY_ORGANIZATION,
  Organization,
} from 'src/app/interfaces/organization';
import { ResType } from 'src/app/shared/enum';
import {
  arrayContainsObjWithId,
  getById,
  removeMatchedIdFromArray,
} from 'src/app/shared/utils';

import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ActivatedRoute, Router } from '@angular/router';
import { ModalService } from 'src/app/services/common/modal.service';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import { UtilsService } from 'src/app/services/common/utils.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: [
    '../../shared/scss/buttons.scss',
    './organization.component.scss',
  ],
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
    private orgDataService: OrgDataService,
    private userDataService: UserDataService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
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

  async init(): Promise<void> {
    // get rules
    (await this.ruleDataService.list()).subscribe((rules) => {
      this.rules = rules;
    });
    // TODO this has a nested subscribe, fix that
    this.activatedRoute.paramMap.subscribe((params) => {
      let new_id = this.utilsService.getId(params, ResType.ORGANIZATION);
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
  }

  async setup() {
    (await this.orgDataService.list()).subscribe((orgs: Organization[]) => {
      this.organizations = orgs;
    });

    // get all organizations that the user is allowed to see
    this.current_organization = getById(this.organizations, this.route_org_id);

    // set the currently requested organization's users/roles/etc
    this.setCurrOrganizationDetails();
  }

  private _allowedToSeeOrg(id: number): boolean {
    /* returns true if organizaiton with certain id exists and the logged-in
       user is allowed to see it */
    return arrayContainsObjWithId(id, this.organizations);
  }

  async setCurrOrganizationDetails(): Promise<void> {
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
    // TODO if a user is assigned a role from another organization that is not
    // the root organization, it will not be shown... consider if that is
    // desirable
    this.roles = await this.roleDataService.org_list(
      this.current_organization.id
    );
    this.roles_assignable = await this.userPermission.getAssignableRoles(
      this.roles
    );
    this.setRoleMetadata();

    // collect users for current organization
    this.setUsers();
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

  async setUsers(): Promise<void> {
    this.organization_users = await this.userDataService.org_list(
      this.route_org_id,
      this.roles,
      this.rules
    );
    for (let user of this.organization_users) {
      user.is_logged_in = user.id === this.loggedin_user.id;
    }
  }

  editOrganization(org: Organization): void {
    this.orgDataService.set(org);
  }

  editUser(user: User): void {
    this.userDataService.set(user);
  }

  createUser(): void {
    this.userDataService.set(getEmptyUser());
  }

  deleteUser(user: User): void {
    this.organization_users = removeMatchedIdFromArray(
      this.organization_users,
      user.id
    );
    this.userDataService.remove(user);
    this.userDataService.remove_from_org(user);
  }

  createRole(): void {
    // initialize role
    let new_role: Role = getEmptyRole();
    new_role.organization_id = this.current_organization.id;

    // use edit mode to fill in all details of new user
    this.roleDataService.set(new_role);
  }

  async deleteRole(role: Role): Promise<void> {
    // remove role
    this.roles = removeMatchedIdFromArray(this.roles, role.id);
    // set data on which roles user can assign, how many roles there are for
    // the current organization
    this.roles_assignable = await this.userPermission.getAssignableRoles(
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
