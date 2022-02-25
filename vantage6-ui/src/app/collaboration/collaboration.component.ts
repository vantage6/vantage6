import { Component, OnInit } from '@angular/core';

import { Node } from 'src/app/interfaces/node';
import { EMPTY_USER, User } from 'src/app/interfaces/user';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { OrganizationInCollaboration } from 'src/app/interfaces/organization';
import { arrayContainsObjWithId } from '../shared/utils';

import { UserPermissionService } from '../auth/services/user-permission.service';
import { ApiNodeService } from '../node/services/api-node.service';
import { ApiOrganizationService } from '../organization/services/api-organization.service';
import { ApiCollaborationService } from './services/api-collaboration.service';

@Component({
  selector: 'app-collaboration',
  templateUrl: './collaboration.component.html',
  styleUrls: ['../shared/scss/buttons.scss', './collaboration.component.scss'],
})
export class CollaborationComponent implements OnInit {
  organizations: OrganizationInCollaboration[] = [];
  nodes: Node[] = [];
  collaborations: Collaboration[] = [];
  other_collaborations: Collaboration[] = [];
  loggedin_user: User = EMPTY_USER;

  constructor(
    public userPermission: UserPermissionService,
    private organizationService: ApiOrganizationService,
    private collaborationService: ApiCollaborationService,
    private nodeService: ApiNodeService
  ) {}

  ngOnInit(): void {
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) {
        this.init();
      }
    });
  }

  async init() {
    this.loggedin_user = this.userPermission.user;

    // get the nodes
    this.nodes = await this.nodeService.getNodes();

    // get the organizations
    this.organizations = await this.organizationService.getOrganizations();

    // get all collaborations
    let all_collaborations = await this.collaborationService.getCollaborations(
      this.organizations
    );

    // add the nodes to the collaborations
    this.addNodesToCollaborations(all_collaborations);

    // Divide collaborations in 2 categories: the ones the logged-in user's
    // organization is involved in and others
    this.collaborations = [];
    this.other_collaborations = [];
    for (let c of all_collaborations) {
      if (
        arrayContainsObjWithId(
          this.loggedin_user.organization_id,
          c.organizations
        )
      ) {
        this.collaborations.push(c);
      } else {
        this.other_collaborations.push(c);
      }
    }
  }

  addNodesToCollaborations(collaborations: Collaboration[]): void {
    for (let c of collaborations) {
      for (let o of c.organizations) {
        for (let n of this.nodes) {
          if (o.id === n.organization_id && c.id === n.collaboration_id) {
            o.node = n;
          }
        }
      }
    }
  }

  deleteCollaboration(col: Collaboration) {}

  editCollaboration(col: Collaboration) {}
}
