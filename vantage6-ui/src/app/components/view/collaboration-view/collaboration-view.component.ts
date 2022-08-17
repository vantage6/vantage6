import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
} from '@angular/core';
import { Router } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import {
  Collaboration,
  EMPTY_COLLABORATION,
} from 'src/app/interfaces/collaboration';
import { getEmptyNode } from 'src/app/interfaces/node';
import { Task } from 'src/app/interfaces/task';
import { Node } from 'src/app/interfaces/node';
import { OrganizationInCollaboration } from 'src/app/interfaces/organization';
import { CollabApiService } from 'src/app/services/api/collaboration-api.service';
import { NodeApiService } from 'src/app/services/api/node-api.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { OpsType, ResType } from 'src/app/shared/enum';
import { removeMatchedIdFromArray } from 'src/app/shared/utils';
import { BaseViewComponent } from '../base-view/base-view.component';
import { ModalMessageComponent } from '../../modal/modal-message/modal-message.component';
import { TaskDataService } from 'src/app/services/data/task-data.service';

@Component({
  selector: 'app-collaboration-view',
  templateUrl: './collaboration-view.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './collaboration-view.component.scss',
  ],
})
export class CollaborationViewComponent
  extends BaseViewComponent
  implements OnInit, OnChanges
{
  @Input() collaboration: Collaboration = EMPTY_COLLABORATION;
  @Output() createdNode = new EventEmitter<Node>();
  orgs_without_nodes: OrganizationInCollaboration[] = [];
  tasks: Task[] = [];
  n_completed_tasks: number = 0;

  constructor(
    private router: Router,
    public userPermission: UserPermissionService,
    private nodeDataService: NodeDataService,
    protected collabDataService: CollabDataService,
    private nodeApiService: NodeApiService,
    protected collabApiService: CollabApiService,
    protected modalService: ModalService,
    private convertJsonService: ConvertJsonService,
    private taskDataService: TaskDataService
  ) {
    super(collabApiService, collabDataService, modalService);
  }

  ngOnChanges(): void {
    if (this.collaboration !== undefined) {
      this.setMissingNodes();
      this.setTasks();
    }
  }

  async setTasks(): Promise<void> {
    this.tasks = await this.taskDataService.collab_list(this.collaboration.id);
    this.n_completed_tasks = this.tasks.filter(
      (task) => task.complete === true
    ).length;
  }

  encryptedText(): string {
    return this.collaboration.encrypted ? 'Yes' : 'No';
  }

  getButtonClasses(org: OrganizationInCollaboration): string {
    let default_classes = 'mat-button btn-link inline ';
    if (!org.node) return default_classes;
    else if (org.node.is_online) return default_classes + 'btn-online';
    else return default_classes + 'btn-offline';
  }

  setMissingNodes(): void {
    this.orgs_without_nodes = [];
    for (let org of this.collaboration.organizations) {
      if (!org.node) {
        this.orgs_without_nodes.push(org);
      }
    }
  }

  isDisabled(org: OrganizationInCollaboration): boolean {
    return (
      org.node === undefined ||
      !this.userPermission.can(OpsType.VIEW, ResType.NODE, org.id)
    );
  }

  getNodeButtonText(org: OrganizationInCollaboration): string {
    let online_text: string = ' ';
    let user_can_view: boolean = this.userPermission.can(
      OpsType.VIEW,
      ResType.NODE,
      org.id
    );
    if (org.node || !user_can_view) {
      online_text += org.node?.is_online ? '(online)' : '(offline)';
    } else if (user_can_view) {
      online_text += '(not registered)';
    } else {
      online_text += '(unknown status)';
    }
    return org.name + online_text;
  }

  goToNode(org: OrganizationInCollaboration): void {
    if (org.node) {
      this.nodeDataService.save(org.node);
      this.router.navigate([`/node/${org.node.id}/view/${org.id}`]);
    }
  }

  goToOrg(org: OrganizationInCollaboration): void {
    this.router.navigate([`organization/${org.id}`]);
  }

  createNode(org: OrganizationInCollaboration): void {
    let new_node = getEmptyNode();
    new_node.name = `${this.collaboration.name} - ${org.name}`;
    new_node.organization_id = org.id;
    new_node.collaboration_id = this.collaboration.id;
    this.nodeApiService.create(new_node).subscribe(
      (node_json) => {
        this.modalService.openMessageModal(ModalMessageComponent, [
          `The node '${node_json.name}' has been created! You can now generate a
configuration file for the node using 'vnode new'.`,
          'Please insert the following API key into your configuration file:',
          node_json.api_key,
        ]);
        // Remove the organization from organizations for which no node is
        // present
        this.orgs_without_nodes = removeMatchedIdFromArray(
          this.orgs_without_nodes,
          org.id
        );
        // set the new node as part of the organization
        org.node = this.convertJsonService.getNode(node_json);
        // store the node
        this.nodeDataService.save(org.node);
        this.createdNode.emit(org.node);
      },
      (error) => {
        this.modalService.openMessageModal(ModalMessageComponent, [
          'Error:',
          error.error.msg,
        ]);
      }
    );
  }

  async delete(): Promise<void> {
    // delete nodes
    for (let org of this.collaboration.organizations) {
      if (org.node) {
        await this.nodeApiService.delete(org.node).toPromise();
        this.nodeDataService.remove(org.node);
      }
    }
    super.delete(this.collaboration);
  }

  askConfirmDelete(): void {
    super.askConfirmDelete(
      this.collaboration,
      ResType.COLLABORATION,
      'Note that any registered nodes in this collaboration will also be deleted.'
    );
  }
}
