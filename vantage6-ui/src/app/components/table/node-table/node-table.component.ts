import { AfterViewInit, Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { TableComponent } from '../base-table/table.component';
import { Node, NodeWithOrg } from 'src/app/interfaces/node';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { deepcopy, getById, parseId } from 'src/app/shared/utils';
import { OpsType, ResType, ScopeType } from 'src/app/shared/enum';
import { ModalService } from 'src/app/services/common/modal.service';
import { allPages } from 'src/app/interfaces/utils';

export enum DisplayMode {
  COL = 'collaboration',
  ORG = 'organization',
  ALL = 'all',
}

@Component({
  selector: 'app-node-table',
  templateUrl: './node-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../table/base-table/table.component.scss',
    './node-table.component.scss',
  ],
})
export class NodeTableComponent
  extends TableComponent
  implements OnInit, AfterViewInit
{
  collaborations: Collaboration[] = [];
  current_collaboration: Collaboration | null;
  displayedColumns: string[] = ['id', 'name', 'organization', 'collaboration'];
  displayMode = DisplayMode.ALL;

  constructor(
    private router: Router,
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private nodeDataService: NodeDataService,
    private orgDataService: OrgDataService,
    private collabDataService: CollabDataService,
    protected modalService: ModalService
  ) {
    super(activatedRoute, userPermission, modalService);
  }

  async init(): Promise<void> {
    // TODO only get collabs and orgs that are in the nodes
    (await this.orgDataService.list(false, allPages())).subscribe((orgs) => {
      this.organizations = orgs;
    });

    (await this.collabDataService.list(false, allPages())).subscribe((cols) => {
      this.collaborations = cols;
    });

    this.readRoute();
  }

  ngAfterViewInit(): void {
    super.ngAfterViewInit();
    this.dataSource.sortingDataAccessor = (item: any, property: any) => {
      let sorter: any;
      if (property === 'organization') {
        sorter = item.organization.name;
      } else if (property === 'collaboration') {
        sorter = item.collaboration.name;
      } else {
        sorter = item[property];
      }
      return this.sortBy(sorter);
    };
  }

  async readRoute() {
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
    await this.setResources();

    await this.addHelperResources();

    this.renewTable();
    this.modalService.closeLoadingModal();
  }

  async addHelperResources(): Promise<void> {
    await this.addCollaborationsToResources();

    await this.addOrganizationsToResources();
  }

  async renewTable(): Promise<void> {
    this.dataSource.data = this.resources;
  }

  protected async setResources() {
    if (this.displayMode === DisplayMode.ORG) {
      (
        await this.nodeDataService.org_list(this.route_org_id as number)
      ).subscribe((org_nodes: Node[]) => {
        this.resources = deepcopy(org_nodes);
        this.addHelperResources();
      });
    } else if (this.displayMode === DisplayMode.COL) {
      (
        await this.nodeDataService.collab_list(this.route_org_id as number)
      ).subscribe((nodes) => {
        this.resources = deepcopy(nodes);
        this.addHelperResources();
      });
    } else {
      (await this.nodeDataService.list()).subscribe((nodes: Node[]) => {
        this.resources = deepcopy(nodes);
        this.addHelperResources();
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

  getNameDropdown() {
    if (this.current_organization) return this.current_organization.name;
    else if (this.current_collaboration) return this.current_collaboration.name;
    else return 'All';
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

  getMatchingNode(old_node: Node) {
    // the nodes in this.resources are observables and updated automatically,
    // but the nodes in the table are not automatically updated. Here we pass a
    // node that is displayed on the datatable to obtain the more recently
    // updated node for display in the detailed nodeViewComponent
    return getById(this.resources, old_node.id);
  }
}
