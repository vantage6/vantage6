import { Component, OnInit } from '@angular/core';

import { UserPermissionService } from '../auth/services/user-permission.service';
import { Organization } from '../organization/interfaces/organization';
import { ApiOrganizationService } from '../organization/services/api-organization.service';
import { arrayContainsObjWithId } from '../shared/utils';
import { EMPTY_USER, User } from '../user/interfaces/user';
import { Collaboration } from './interfaces/collaboration';
import { ApiCollaborationService } from './services/api-collaboration.service';

@Component({
  selector: 'app-collaboration',
  templateUrl: './collaboration.component.html',
  styleUrls: ['./collaboration.component.scss'],
})
export class CollaborationComponent implements OnInit {
  organizations: Organization[] = [];
  collaborations: Collaboration[] = [];
  other_collaborations: Collaboration[] = [];
  loggedin_user: User = EMPTY_USER;

  constructor(
    public userPermission: UserPermissionService,
    private organizationService: ApiOrganizationService,
    private collaborationService: ApiCollaborationService
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

    // initialize organizations
    this.organizations = await this.organizationService.getOrganizations();

    // get all collaborations
    let all_collaborations = await this.collaborationService.getCollaborations(
      this.organizations
    );
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

  deleteCollaboration(col: Collaboration) {}
  editCollaboration(col: Collaboration) {}
}
