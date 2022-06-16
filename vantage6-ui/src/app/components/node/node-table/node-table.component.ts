import { AfterViewInit, Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { TableComponent } from '../../base/table/table.component';
import { Node, NodeWithOrg } from 'src/app/interfaces/node';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { deepcopy, parseId } from 'src/app/shared/utils';
import { OpsType, ResType, ScopeType } from 'src/app/shared/enum';

enum DisplayMode {
  COL = 'collaboration',
  ORG = 'organization',
  ALL = 'all',
}

@Component({
  selector: 'app-node-table',
  templateUrl: './node-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../base/table/table.component.scss',
    './node-table.component.scss',
  ],
})
export class NodeTableComponent
  extends TableComponent
  implements OnInit, AfterViewInit
{
  collaborations: Collaboration[] = [];
  current_collaboration: Collaboration | null;
  displayedColumns: string[] = [
    'name',
    'organization',
    'collaboration',
    'details',
  ];
  displayMode = DisplayMode.ALL;

  constructor(
    private router: Router,
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

  async readRoute() {
    // TODO refactor
    if (this.router.url.includes('org')) {
      this.displayMode = DisplayMode.ORG;
    } else if (this.router.url.includes('collab')) {
      this.displayMode = DisplayMode.COL;
    } else {
      this.displayMode = DisplayMode.ALL;
    }

    this.activatedRoute.paramMap.subscribe((params: any) => {
      let id: any;
      if (this.displayMode === DisplayMode.ORG) {
        id = parseId(params.get('org_id'));
      } else if (this.displayMode === DisplayMode.COL) {
        id = parseId(params.get('collab_id'));
      }
      if (isNaN(id)) {
        this.route_org_id = null;
        this.current_organization = null;
        this.current_collaboration = null;
      } else {
        this.route_org_id = id;
        if (this.displayMode === DisplayMode.ORG) {
          this.setCurrentOrganization();
          this.current_collaboration = null;
        } else {
          this.setCurrentCollaboration();
          this.current_organization = null;
        }
      }
      this.setup();
    });
  }

  async setup() {
    await super.setup();
    this.addCollaborationsToResources();
  }

  protected async setResources() {
    if (this.displayMode === DisplayMode.ORG) {
      this.resources = await this.nodeDataService.org_list(
        this.route_org_id as number
      );
    } else if (this.displayMode === DisplayMode.COL) {
      this.resources = await this.nodeDataService.collab_list(
        this.route_org_id as number
      );
    } else {
      (await this.nodeDataService.list()).subscribe((nodes: Node[]) => {
        this.resources = nodes;
      });
    }
    // make a copy to prevent that changes in these resources are directly
    // reflected in the resources within dataServices
    this.resources = deepcopy(this.resources);
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

  getCollabNameDropdown(): string {
    return this.current_collaboration ? this.current_collaboration.name : 'All';
  }

  setCurrentCollaboration(): void {
    for (let col of this.collaborations) {
      if (col.id === this.route_org_id) {
        this.current_collaboration = col;
        break;
      }
    }
  }

  getSelectDropdownText(): string {
    let entity: string = '';
    if (
      this.userPermission.hasPermission(
        OpsType.VIEW,
        ResType.ORGANIZATION,
        ScopeType.COLLABORATION
      ) ||
      this.userPermission.hasPermission(
        OpsType.VIEW,
        ResType.ORGANIZATION,
        ScopeType.GLOBAL
      )
    ) {
      entity = 'organization';
    }
    if (
      this.userPermission.hasPermission(
        OpsType.VIEW,
        ResType.COLLABORATION,
        ScopeType.ANY
      )
    ) {
      if (entity) entity += '/';
      entity += 'collaboration';
    }
    return `Select ${entity} to view:`;
  }
}
