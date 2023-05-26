import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import {
  Collaboration,
  EMPTY_COLLABORATION,
} from 'src/app/interfaces/collaboration';
import { Node } from 'src/app/interfaces/node';
import {
  Organization,
  OrganizationInCollaboration,
} from 'src/app/interfaces/organization';
import { ModalService } from 'src/app/services/common/modal.service';
import { UtilsService } from 'src/app/services/common/utils.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { ResType } from 'src/app/shared/enum';
import { BaseSingleViewComponent } from '../base-single-view/base-single-view.component';
import { allPages } from 'src/app/interfaces/utils';

@Component({
  selector: 'app-collaboration-view-single',
  templateUrl: './collaboration-view-single.component.html',
  styleUrls: ['./collaboration-view-single.component.scss'],
})
export class CollaborationViewSingleComponent
  extends BaseSingleViewComponent
  implements OnInit
{
  organizations: OrganizationInCollaboration[] = [];
  nodes: Node[] = [];
  collaboration: Collaboration = EMPTY_COLLABORATION;

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private nodeDataService: NodeDataService,
    private collabDataService: CollabDataService,
    protected utilsService: UtilsService,
    private orgDataService: OrgDataService,
    protected modalService: ModalService
  ) {
    super(
      activatedRoute,
      userPermission,
      utilsService,
      ResType.COLLABORATION,
      modalService
    );
  }

  async setResources() {
    this.setNodes();

    this.setOrganizations();

    this.setCollaboration();
  }

  async setCollaboration(): Promise<void> {
    (await this.collabDataService.get(this.route_id as number, true)).subscribe(
      (collab) => {
        this.collaboration = collab;
      }
    );
  }

  async setOrganizations(): Promise<void> {
    // TODO only get organizations that belong to this collab
    (await this.orgDataService.list(false, allPages())).subscribe(
      (orgs: Organization[]) => {
        this.organizations = orgs;
      }
    );
  }

  async setNodes(): Promise<void> {
    (await this.nodeDataService.collab_list(this.route_id as number)).subscribe(
      (nodes: Node[]) => {
        this.nodes = nodes;
      }
    );
  }
}
