import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
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

@Component({
  selector: 'app-collaboration-edit',
  templateUrl: './collaboration-edit.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './collaboration-edit.component.scss',
  ],
})
export class CollaborationEditComponent implements OnInit {
  collaboration: Collaboration = EMPTY_COLLABORATION;
  all_organizations: OrganizationInCollaboration[] = [];
  organizations_not_in_collab: OrganizationInCollaboration[] = [];
  is_being_created: boolean = false;
  is_register_nodes: boolean = true;

  constructor(
    private activatedRoute: ActivatedRoute,
    private collabApiService: ApiCollaborationService,
    private nodeApiService: ApiNodeService,
    private collabDataService: CollabDataService,
    private orgDataService: OrgDataService,
    private nodeDataService: NodeDataService,
    private modalService: ModalService,
    private utilsService: UtilsService,
    private convertJsonService: ConvertJsonService
  ) {}

  ngOnInit(): void {
    this.collaboration = deepcopy(EMPTY_COLLABORATION);
    this.init();
  }

  async init(): Promise<void> {
    // first obtain organizations, which are required to get the collaboration
    (await this.orgDataService.list()).subscribe((organizations) => {
      this.all_organizations = organizations;
      this.organizations_not_in_collab = deepcopy(organizations);
    });

    // subscribe to id parameter in route to change edited collaboration if
    // required
    this.activatedRoute.paramMap.subscribe((params) => {
      let id = this.utilsService.getId(params, ResType.COLLABORATION);
      if (id === EMPTY_COLLABORATION.id) {
        this.is_being_created = true;
        return; // cannot get collaboration
      }
      this.setCollaboration(id);
    });
  }

  async setCollaboration(id: number) {
    this.collaboration = await this.collabDataService.get(
      id,
      this.all_organizations
    );
    // remove organizations that are already in collaboration from the
    // organizations that can be added to it
    removeMatchedIdsFromArray(
      this.all_organizations,
      getIdsFromArray(this.collaboration.organizations)
    );
  }

  saveEdit(): void {
    let request;
    if (this.is_being_created) {
      request = this.collabApiService.create(this.collaboration);
    } else {
      request = this.collabApiService.update(this.collaboration);
    }

    request.subscribe(
      (new_collab_json) => {
        this.processCollaborationChanges(new_collab_json);
      },
      (error) => {
        this.modalService.openMessageModal(ModalMessageComponent, [
          'Error:',
          error.error.msg,
        ]);
      }
    );
  }

  async processCollaborationChanges(collab_json: any) {
    if (this.is_being_created) {
      await this.addNewCollaboration(collab_json);
    }
    // go to previous page only after adding the new collaboration
    this.utilsService.goToPreviousPage();
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

  cancelEdit(): void {
    this.utilsService.goToPreviousPage();
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
      ...this.organizations_not_in_collab,
      org,
    ];
  }
}
