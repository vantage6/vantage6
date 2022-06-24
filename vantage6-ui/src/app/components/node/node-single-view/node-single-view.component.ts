import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { EMPTY_NODE, NodeWithOrg } from 'src/app/interfaces/node';
import { Organization } from 'src/app/interfaces/organization';
import { UtilsService } from 'src/app/services/common/utils.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { ResType } from 'src/app/shared/enum';
import { deepcopy } from 'src/app/shared/utils';
import { BaseSingleViewComponent } from '../../base/base-single-view/base-single-view.component';

@Component({
  selector: 'app-node-single-view',
  templateUrl: './node-single-view.component.html',
  styleUrls: ['./node-single-view.component.scss'],
})
export class NodeSingleViewComponent
  extends BaseSingleViewComponent
  implements OnInit
{
  node: NodeWithOrg = EMPTY_NODE;

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private nodeDataService: NodeDataService,
    private orgDataService: OrgDataService,
    private collabDataService: CollabDataService,
    protected utilsService: UtilsService
  ) {
    super(activatedRoute, userPermission, utilsService, ResType.NODE);
  }

  async setResources(): Promise<void> {
    await this.setNode();
    await this.setOrganization();
    this.setCollaboration();
  }

  async setNode(): Promise<void> {
    this.node = deepcopy(
      await this.nodeDataService.get(this.route_id as number)
    );
  }

  async setOrganization(): Promise<void> {
    this.node.organization = await this.orgDataService.get(
      this.node.organization_id
    );
  }
  async setCollaboration(): Promise<void> {
    this.node.collaboration = await this.collabDataService.get(
      this.node.collaboration_id,
      [this.node.organization as Organization]
    );
  }
}
