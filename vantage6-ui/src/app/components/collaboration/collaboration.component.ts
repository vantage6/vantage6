import { Component, OnInit } from '@angular/core';
import { take } from 'rxjs/operators';

import { Node } from 'src/app/interfaces/node';
import { EMPTY_USER, User } from 'src/app/interfaces/user';
import { Collaboration } from 'src/app/interfaces/collaboration';
import {
  Organization,
  OrganizationInCollaboration,
} from 'src/app/interfaces/organization';
import {
  arrayContainsObjWithId,
  removeMatchedIdFromArray,
} from 'src/app/shared/utils';

import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';

@Component({
  selector: 'app-collaboration',
  templateUrl: './collaboration.component.html',
  styleUrls: [
    '../../shared/scss/buttons.scss',
    './collaboration.component.scss',
  ],
})
export class CollaborationComponent implements OnInit {
  organizations: OrganizationInCollaboration[] = [];
  nodes: Node[] = [];
  all_collaborations: Collaboration[] = [];
  my_collaborations: Collaboration[] = [];
  other_collaborations: Collaboration[] = [];
  loggedin_user: User = EMPTY_USER;

  constructor(
    public userPermission: UserPermissionService,
    private nodeDataService: NodeDataService,
    public collabDataService: CollabDataService,
    private orgDataService: OrgDataService
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

    // set the nodes
    await this.setNodes(false);

    // set the organizations
    await this.setOrganizations(false);

    // set all collaborations
    this.setCollaborations();
  }

  async setCollaborations(): Promise<void> {
    (
      await this.collabDataService.list(this.organizations, this.nodes)
    ).subscribe((collabs: Collaboration[]) => {
      this.all_collaborations = collabs;
      this.updateCollaborations();
    });
  }

  async setOrganizations(update_collabs: boolean = true): Promise<void> {
    (await this.orgDataService.list()).subscribe((orgs: Organization[]) => {
      this.organizations = orgs;
      if (update_collabs) this.setCollaborations();
    });
  }

  async setNodes(update_collabs: boolean = true): Promise<void> {
    (await this.nodeDataService.list()).subscribe((nodes: Node[]) => {
      this.nodes = nodes;
      if (update_collabs) this.setCollaborations();
    });
  }

  updateCollaborations(): void {
    if (this.all_collaborations.length === 0) return;

    // Divide collaborations in 2 categories: the ones the logged-in user's
    // organization is involved in and others
    this.my_collaborations = [];
    this.other_collaborations = [];
    for (let c of this.all_collaborations) {
      if (
        arrayContainsObjWithId(
          this.loggedin_user.organization_id,
          c.organizations
        )
      ) {
        this.my_collaborations.push(c);
      } else {
        this.other_collaborations.push(c);
      }
    }
  }

  // TODO the two functions below are copied in a few locations. Refactor!
  deleteCollaboration(col: Collaboration) {
    // delete nodes of collaboration
    for (let org of col.organizations) {
      if (org.node) {
        this.nodeDataService.remove(org.node);
        removeMatchedIdFromArray(this.nodes, org.node.id);
      }
    }
    // delete collaboration
    this.all_collaborations = removeMatchedIdFromArray(
      this.all_collaborations,
      col.id
    );
    this.updateCollaborations();
    this.collabDataService.remove(col);
  }
}
