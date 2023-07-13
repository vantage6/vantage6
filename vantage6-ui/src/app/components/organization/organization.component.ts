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
  arrayContains,
  arrayContainsObjWithId,
  filterArrayByProperty,
  getById,
  removeDuplicateIds,
  removeMatchedIdFromArray,
  removeValueFromArray,
} from 'src/app/shared/utils';

import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ActivatedRoute, Router } from '@angular/router';
import { ModalService } from 'src/app/services/common/modal.service';
import { UtilsService } from 'src/app/services/common/utils.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { FileService } from 'src/app/services/common/file.service';
import { allPages, defaultFirstPage } from 'src/app/interfaces/utils';

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
  users: User[] = [];
  roles: Role[] = [];
  nodes: Node[] = [];
  organization_nodes: Node[] = [];
  collaborations: Collaboration[] = [];
  MAX_ITEMS_DISPLAY: number = 5;
  expanded_collab_ids: number[] = [];

  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private orgDataService: OrgDataService,
    private userDataService: UserDataService,
    public roleDataService: RoleDataService,
    private nodeDataService: NodeDataService,
    private collabDataService: CollabDataService,
    private modalService: ModalService,
    private utilsService: UtilsService,
    private fileService: FileService
  ) {}

  // TODO Now it is shown that there are no users/roles until they are loaded,
  // instead should say that they are being loaded
  ngOnInit(): void {
    this.modalService.openLoadingModal();
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) this.init();
    });
  }

  async init(): Promise<void> {
    this.loggedin_user = this.userPermission.user;
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
    (await this.orgDataService.list(false, allPages())).subscribe(
      (orgs: Organization[]) => {
        this.organizations = orgs;
      }
    );

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
      this.modalService.openMessageModal([
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

    // TODO there are things that can be parallelized below, but they should
    // still be awaited... refactor

    // first collect roles for current organization. This is done before
    // collecting the users so that the users can possess these roles
    (
      await this.roleDataService.org_list(this.current_organization.id)
    ).subscribe((roles) => {
      this.roles = roles;
      this.onRenewalRoles();
    });

    // collect users for current organization
    await this.setUsers();

    // collect collaborations for current organization
    await this.setCollaborations();

    // collect nodes for current organization
    await this.setNodes();

    this.modalService.closeLoadingModal();
  }

  onRenewalRoles() {
    this.roles = this.sortRoles(this.roles);
  }

  sortRoles(roles: Role[]): Role[] {
    //sort roles: put roles of current organization first, then generic roles
    roles.sort((a, b) => b.organization_id - a.organization_id);
    return roles;
  }

  async setUsers(): Promise<void> {
    (await this.userDataService.org_list(this.route_org_id)).subscribe(
      (users) => {
        // TODO users should be automatically updated... it's observable now so remove other references to it
        this.users = users;
        for (let user of this.users) {
          user.is_logged_in = user.id === this.loggedin_user.id;
        }
      }
    );
  }

  async setNodes(): Promise<void> {
    (await this.nodeDataService.org_list(this.route_org_id)).subscribe(
      (org_nodes: Node[]) => {
        this.organization_nodes = org_nodes;
      }
    );

    // obtain the nodes relevant to the collaborations
    this.nodes = [];
    for (let collab of this.collaborations) {
      (await this.nodeDataService.collab_list(collab.id)).subscribe((nodes) => {
        this.nodes = filterArrayByProperty(
          this.nodes,
          'collaboration_id',
          collab.id,
          false
        );
        this.nodes.push(...nodes);
      });
    }
    this.nodes = removeDuplicateIds(this.nodes);
  }

  async setCollaborations(): Promise<void> {
    (await this.collabDataService.list_with_params(
      defaultFirstPage(), {'organization_id': this.route_org_id}
    )).subscribe((collabs) => {
      this.collaborations = collabs;
    });
  }

  editOrganization(org: Organization): void {
    this.orgDataService.save(org);
  }

  deleteUser(user: User): void {
    this.users = removeMatchedIdFromArray(this.users, user.id);
  }

  deleteNode(node: Node): void {
    this.nodes = removeMatchedIdFromArray(this.nodes, node.id);
  }

  async deleteRole(role: Role): Promise<void> {
    // remove role
    this.roles = removeMatchedIdFromArray(this.roles, role.id);
    // delete this role from any user it was assigned to (this is also done
    // separately in the backend)
    this.deleteRoleFromUsers(role);
  }

  private deleteRoleFromUsers(role: Role): void {
    for (let user of this.users) {
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
        `public_key_organization_${this.current_organization.name}.txt`
      );
  }

  getNodeButtonText(node: Node): string {
    const online_text = node.is_online ? ' (online)' : ' (offline)';
    return node.name + online_text;
  }

  getButtonClasses(node: Node): string {
    let default_classes = 'mat-button btn-link inline ';
    if (node.is_online) return default_classes + 'btn-online';
    else return default_classes + 'btn-offline';
  }

  isExpanded(col: Collaboration): boolean {
    return arrayContains(this.expanded_collab_ids, col.id);
  }

  openExpansionPanel(col: Collaboration): void {
    this.expanded_collab_ids.push(col.id);
  }
  closeExpansionPanel(col: Collaboration): void {
    this.expanded_collab_ids = removeValueFromArray(
      this.expanded_collab_ids,
      col.id
    );
  }

  getUserTitle(user: User): string {
    return user.first_name || user.last_name
      ? `${user.first_name} ${user.last_name}`
      : user.username;
  }
}
