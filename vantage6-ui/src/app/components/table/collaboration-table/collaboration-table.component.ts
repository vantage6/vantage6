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
    (await this.orgDataService.list()).subscribe((orgs) => {
      this.organizations = orgs;
    });

    this.readRoute();
  }

  async setResources(): Promise<void> {
    if (this.isShowingSingleOrg()) {
      (
        await this.collabDataService.org_list(this.route_org_id as number)
      ).subscribe((collabs) => {
        this.resources = collabs;
      });
    } else {
      (await this.collabDataService.list()).subscribe(
        (collabs: Collaboration[]) => {
          this.resources = collabs;
        }
      );
    }
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
