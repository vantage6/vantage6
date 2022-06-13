import { AfterViewInit, Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { TableComponent } from '../../table/table.component';
import { Node, NodeWithOrg } from 'src/app/interfaces/node';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { Collaboration } from 'src/app/interfaces/collaboration';

@Component({
  selector: 'app-node-table',
  templateUrl: './node-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../table/table.component.scss',
    './node-table.component.scss',
  ],
})
export class NodeTableComponent
  extends TableComponent
  implements OnInit, AfterViewInit
{
  collaborations: Collaboration[] = [];
  displayedColumns: string[] = [
    'name',
    'organization',
    'collaboration',
    'details',
  ];

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private nodeDataService: NodeDataService,
    private orgDataService: OrgDataService,
    private collabDataService: CollabDataService
  ) {
    super(activatedRoute, userPermission);
  }

  async init(): Promise<void> {
    (await this.orgDataService.list()).subscribe((orgs) => {
      this.organizations = orgs;
    });

    (await this.collabDataService.list(this.organizations)).subscribe(
      (cols) => {
        this.collaborations = cols;
      }
    );

    this.readRoute();
  }

  async setup() {
    await super.setup();
    this.addCollaborationsToResources();
  }

  protected async setResources() {
    if (this.isShowingSingleOrg()) {
      this.resources = await this.nodeDataService.org_list(
        this.route_org_id as number
      );
    } else {
      (await this.nodeDataService.list()).subscribe((nodes: Node[]) => {
        this.resources = nodes;
      });
    }
  }

  protected async addCollaborationsToResources() {
    for (let r of this.resources as NodeWithOrg[]) {
      for (let col of this.collaborations) {
        if (col.id === r.collaboration_id) {
          r.collaboration = col;
          break;
        }
      }
    }
  }
}
