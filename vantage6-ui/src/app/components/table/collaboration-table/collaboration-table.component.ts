import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { Node } from 'src/app/interfaces/node';
import { OrganizationInCollaboration } from 'src/app/interfaces/organization';
import { ModalService } from 'src/app/services/common/modal.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { TableComponent } from '../base-table/table.component';

@Component({
  selector: 'app-collaboration-table',
  templateUrl: './collaboration-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../table/base-table/table.component.scss',
    './collaboration-table.component.scss',
  ],
})
export class CollaborationTableComponent
  extends TableComponent
  implements OnInit
{
  organizations: OrganizationInCollaboration[] = [];
  nodes: Node[] = [];

  displayedColumns: string[] = ['id', 'name', 'organizations', 'encrypted'];

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private collabDataService: CollabDataService,
    private orgDataService: OrgDataService,
    private nodeDataService: NodeDataService,
    protected modalService: ModalService
  ) {
    super(activatedRoute, userPermission, modalService);
  }

  async init() {
    // get organizations
    this.organizations = await this.orgDataService.list();

    this.readRoute();
  }

  async setResources(): Promise<void> {
    await this.setNodes();
    if (this.isShowingSingleOrg()) {
      this.resources = await this.collabDataService.org_list(
        this.route_org_id as number,
        this.organizations,
        this.nodes
      );
    } else {
      this.resources = await this.collabDataService.list(
        this.organizations,
        this.nodes
      );
    }
  }

  async addNodes() {
    // set the nodes
    await this.setNodes();

    // organizations and nodes to collaborations
    this.resources = await this.collabDataService.addOrgsAndNodes(
      this.resources as Collaboration[],
      this.organizations,
      this.nodes
    );
  }

  async setNodes(): Promise<void> {
    this.nodes = await this.nodeDataService.list();
    // TODO now we gather all nodes
    // this.nodes = [];
    // for (let collab of this.resources) {
    //   const nodes = await this.nodeDataService.collab_list(collab.id);
    //   this.nodes.push(...nodes);
    // }
    // this.nodes = removeDuplicateIds(this.nodes);
  }

  isEncryptedText(collab: Collaboration): string {
    return collab.encrypted ? 'Yes' : 'No';
  }

  getOrgsText(collab: Collaboration): string {
    const org_names = collab.organizations.map((org) => {
      return org.name;
    });
    return org_names.join(', ');
  }
}
