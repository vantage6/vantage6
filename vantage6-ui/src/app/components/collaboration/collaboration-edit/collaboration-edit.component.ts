import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import {
  Collaboration,
  EMPTY_COLLABORATION,
} from 'src/app/interfaces/collaboration';
import { ApiCollaborationService } from 'src/app/services/api/api-collaboration.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { UtilsService } from 'src/app/services/common/utils.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { ResType } from 'src/app/shared/enum';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import { OrganizationInCollaboration } from 'src/app/interfaces/organization';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import {
  deepcopy,
  getIdsFromArray,
  removeMatchedIdFromArray,
  removeMatchedIdsFromArray,
} from 'src/app/shared/utils';
import { ApiNodeService } from 'src/app/services/api/api-node.service';
import { Node, getEmptyNode } from 'src/app/interfaces/node';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { BaseEditComponent } from '../../base/base-edit/base-edit.component';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';

@Component({
  selector: 'app-collaboration-edit',
  templateUrl: './collaboration-edit.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './collaboration-edit.component.scss',
  ],
})
export class CollaborationEditComponent
  extends BaseEditComponent
  implements OnInit
{
  collaboration: Collaboration = EMPTY_COLLABORATION;
  all_organizations: OrganizationInCollaboration[] = [];
  organizations_not_in_collab: OrganizationInCollaboration[] = [];
  is_register_nodes: boolean = true;

  constructor(
    protected router: Router,
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    protected collabApiService: ApiCollaborationService,
    private nodeApiService: ApiNodeService,
    protected collabDataService: CollabDataService,
    private orgDataService: OrgDataService,
    private nodeDataService: NodeDataService,
    protected modalService: ModalService,
    protected utilsService: UtilsService,
    private convertJsonService: ConvertJsonService
  ) {
    super(
      router,
      activatedRoute,
      userPermission,
      utilsService,
      collabApiService,
      collabDataService,
      modalService
    );
  }

  async init(): Promise<void> {
    // first obtain organizations, which are required to get the collaboration
    (await this.orgDataService.list()).subscribe((organizations) => {
      this.all_organizations = organizations;
      this.organizations_not_in_collab = deepcopy(organizations);
    });

    this.readRoute();
  }

  async setupEdit(id: number) {
    this.collaboration = await this.collabDataService.get(
      id,
      this.all_organizations
    );
    // remove organizations that are already in collaboration from the
    // organizations that can be added to it
    this.organizations_not_in_collab = removeMatchedIdsFromArray(
      this.organizations_not_in_collab,
      getIdsFromArray(this.collaboration.organizations)
    );
  }

  setupCreate(): void {
    // no specific actions required here, just implementing abstract parent
  }

  async save(): Promise<void> {
    let collab_json = await super.save(this.collaboration);
    if (this.isCreate()) {
      await this.addNewCollaboration(collab_json);
    }
  }

  async addNewCollaboration(new_collab_json: any) {
    this.collaboration = this.convertJsonService.getCollaboration(
      new_collab_json,
      this.all_organizations
    );
    this.collabDataService.save(this.collaboration);
    // create the nodes for the new collaboration, and add them to it
    let nodes = await this.createNodes();
    this.collabDataService.addNodesToCollaboration(this.collaboration, nodes);
  }

  async createNodes(): Promise<Node[]> {
    if (!this.is_register_nodes) return [];

    let api_keys: string[] = [];
    let new_nodes: Node[] = [];
    for (let org of this.collaboration.organizations) {
      let new_node = getEmptyNode();
      new_node.name = `${this.collaboration.name} - ${org.name}`;
      new_node.organization_id = org.id;
      new_node.collaboration_id = this.collaboration.id;
      try {
        const node_json = await this.nodeApiService
          .create(new_node)
          .toPromise();
        api_keys.push(`${org.name}: ${node_json.api_key}`);
        new_node.id = node_json.id;
        this.nodeDataService.save(new_node);
        new_nodes.push(new_node);
      } catch (error: any) {
        this.modalService.openMessageModal(ModalMessageComponent, [
          'Error: ' + error.error.msg,
        ]);
      }
    }
    this.modalService.openMessageModal(ModalMessageComponent, [
      'The nodes for your collaboration have been created. They have the following API keys:',
      ...api_keys,
      'Please distribute these API keys to the organizations hosting the nodes.',
    ]);
    return new_nodes;
  }

  addOrg(org: OrganizationInCollaboration): void {
    // add organization to collaboration
    this.collaboration.organizations = [
      ...this.collaboration.organizations,
      org,
    ];
    // remove organization from list that can be added
    this.organizations_not_in_collab = removeMatchedIdFromArray(
      this.organizations_not_in_collab,
      org.id
    );
  }

  removeOrg(org: OrganizationInCollaboration): void {
    // remove organization from collaboration
    this.collaboration.organizations = removeMatchedIdFromArray(
      this.collaboration.organizations,
      org.id
    );
    // add organization to list of organizations that may be added to collab
    this.organizations_not_in_collab = [
      org,
      ...this.organizations_not_in_collab,
    ];
  }
}
