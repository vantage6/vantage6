import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import {
  Collaboration,
  EMPTY_COLLABORATION,
} from 'src/app/interfaces/collaboration';
import { EMPTY_NODE, Node } from 'src/app/interfaces/node';
import {
  Organization,
  OrganizationInCollaboration,
} from 'src/app/interfaces/organization';
import { UtilsService } from 'src/app/services/common/utils.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { ResType } from 'src/app/shared/enum';
import { removeMatchedIdFromArray } from 'src/app/shared/utils';

@Component({
  selector: 'app-collaboration-view-single',
  templateUrl: './collaboration-view-single.component.html',
  styleUrls: ['./collaboration-view-single.component.scss'],
})
export class CollaborationViewSingleComponent implements OnInit {
  route_id: number | null = null;
  organizations: OrganizationInCollaboration[] = [];
  nodes: Node[] = [];
  collaboration: Collaboration = EMPTY_COLLABORATION;

  constructor(
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private nodeDataService: NodeDataService,
    private collabDataService: CollabDataService,
    private utilsService: UtilsService,
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
    this.activatedRoute.paramMap.subscribe((params) => {
      this.route_id = this.utilsService.getId(params, ResType.NODE);
      if (this.route_id === EMPTY_NODE.id) {
        return; // cannot get organization
      }
      this.setup();
    });
  }

  async setup() {
    // TODO organize this in a different way: first get the collaboration, then
    // get ONLY the organizations and nodes relevant for that collab, instead
    // of all of them first and then getting single collaboration
    await this.setNodes(false);

    await this.setOrganizations(false);

    this.setCollaboration();
  }

  async setCollaboration(): Promise<void> {
    this.collaboration = await this.collabDataService.get(
      this.route_id as number,
      this.organizations,
      this.nodes
    );
  }

  async setOrganizations(update_collabs: boolean = true): Promise<void> {
    (await this.orgDataService.list()).subscribe((orgs: Organization[]) => {
      this.organizations = orgs;
      if (update_collabs) this.setCollaboration();
    });
  }

  async setNodes(update_collabs: boolean = true): Promise<void> {
    (await this.nodeDataService.list()).subscribe((nodes: Node[]) => {
      this.nodes = nodes;
      if (update_collabs) this.setCollaboration();
    });
  }

  deleteCollaboration(col: Collaboration) {
    // delete nodes of collaboration
    for (let org of col.organizations) {
      if (org.node) {
        this.nodeDataService.remove(org.node);
        removeMatchedIdFromArray(this.nodes, org.node.id);
      }
    }
    this.collabDataService.remove(col);
    this.utilsService.goToPreviousPage();
  }

  editCollaboration(col: Collaboration) {
    this.collabDataService.save(col);
  }
}
