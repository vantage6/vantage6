import { Component, OnInit } from '@angular/core';

import { EMPTY_USER, User } from 'src/app/interfaces/user';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { Node } from 'src/app/interfaces/node';
import {
  EMPTY_ORGANIZATION,
  getEmptyOrganization,
  Organization,
  OrganizationInCollaboration,
} from 'src/app/interfaces/organization';
import { ResType } from 'src/app/shared/enum';
import {
  arrayContainsObjWithId,
  deepcopy,
  getById,
  removeDuplicateIds,
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
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { FileService } from 'src/app/services/common/file.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: [
    '../../shared/scss/buttons.scss',
    './organization.component.scss',
  ],
})
export class OrganizationComponent implements OnInit {
  organizations: OrganizationInCollaboration[] = [];
  current_organization: OrganizationInCollaboration = getEmptyOrganization();
  route_org_id: number = this.current_organization.id;
  loggedin_user: User = EMPTY_USER;
  organization_users: User[] = [];
  roles: Role[] = [];
  roles_assignable: Role[] = [];
  rules: Rule[] = [];
  nodes: Node[] = [];
  organization_nodes: Node[] = [];
  collaborations: Collaboration[] = [];
  MAX_ITEMS_DISPLAY: number = 5;

  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private orgDataService: OrgDataService,
    private userDataService: UserDataService,
    public roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    private nodeDataService: NodeDataService,
    private collabDataService: CollabDataService,
    private modalService: ModalService,
    private utilsService: UtilsService,
    private fileService: FileService
  ) {}

  // TODO Now it is shown that there are no users/roles until they are loaded,
  // instead should say that they are being loaded
  ngOnInit(): void {
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) this.init();
    });
  }

  async init(): Promise<void> {
    this.loggedin_user = this.userPermission.user;
    // get rules
    (await this.ruleDataService.list()).subscribe((rules) => {
      this.rules = rules;
    });
    this.activatedRoute.paramMap.subscribe((params) => {
      let new_id = this.utilsService.getId(params, ResType.ORGANIZATION);
      if (new_id === EMPTY_ORGANIZATION.id) {
        return; // cannot get organization
      }
      if (new_id !== this.route_org_id) {
        this.route_org_id = new_id;
        this.setup();
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
      return;
    }

    // first collect roles for current organization. This is done before
    // collecting the users so that the users can possess these roles
    this.roles = await this.roleDataService.org_list(
      this.current_organization.id,
      this.rules
    );
    this.roles = await this.sortRoles(this.roles);
    this.roles_assignable = await this.userPermission.getAssignableRoles(
      this.roles
    );

    // collect users for current organization
    this.setUsers();

    // collect collaborations for current organization
    await this.setCollaborations();

    // collect nodes for current organization
    await this.setNodes();
  }

  async sortRoles(roles: Role[]): Promise<Role[]> {
    //sort roles: put roles of current organization first, then generic roles
    roles.sort((a, b) => b.organization_id - a.organization_id);
    return roles;
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

  async setNodes(): Promise<void> {
    this.organization_nodes = await this.nodeDataService.org_list(
      this.route_org_id
    );

    // obtain the nodes relevant to the collaborations
    this.nodes = [];
    for (let collab of this.collaborations) {
      const nodes = await this.nodeDataService.collab_list(collab.id);
      this.nodes.push(...nodes);
    }
    this.nodes = removeDuplicateIds(this.nodes);

    // add the nodes to the collaborations
    // NB deepcopy serves to fire ngOnChanges in child component
    this.collaborations = deepcopy(
      await this.collabDataService.addOrgsAndNodes(
        this.collaborations,
        this.organizations,
        this.nodes
      )
    );
  }

  async setCollaborations(): Promise<void> {
    this.collaborations = await this.collabDataService.org_list(
      this.current_organization.id,
      this.organizations,
      this.nodes
    );
  }

  editOrganization(org: Organization): void {
    this.orgDataService.save(org);
  }

  deleteUser(user: User): void {
    this.organization_users = removeMatchedIdFromArray(
      this.organization_users,
      user.id
    );
  }

  async deleteRole(role: Role): Promise<void> {
    // remove role
    this.roles = removeMatchedIdFromArray(this.roles, role.id);
    // reset data on which roles user can assign
    this.roles_assignable = await this.userPermission.getAssignableRoles(
      this.roles
    );
    // delete this role from any user it was assigned to (this is also done
    // separately in the backend)
    this.deleteRoleFromUsers(role);
  }

  private deleteRoleFromUsers(role: Role): void {
    for (let user of this.organization_users) {
      user.roles = removeMatchedIdFromArray(user.roles, role.id);
    }
  }

  deleteCollaboration(col: Collaboration) {
    // delete nodes of collaboration
    for (let org of col.organizations) {
      if (org.node) {
        removeMatchedIdFromArray(this.nodes, org.node.id);
      }
    }
    // delete collaboration
    this.collaborations = removeMatchedIdFromArray(this.collaborations, col.id);
  }

  downloadPublicKey(): void {
    if (this.current_organization.public_key)
      this.fileService.downloadTxtFile(
        this.current_organization.public_key,
        `public_key_organization_${this.current_organization.name}.pub`
      );
  }
}
