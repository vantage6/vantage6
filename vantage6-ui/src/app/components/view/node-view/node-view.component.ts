import { HttpClient } from '@angular/common/http';
import { Component, Input, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { getEmptyNode, NodeWithOrg } from 'src/app/interfaces/node';
import { NodeApiService } from 'src/app/services/api/node-api.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { NodeDataService } from 'src/app/services/data/node-data.service';
import { ExitMode } from 'src/app/shared/enum';
import { environment } from 'src/environments/environment';
import { BaseViewComponent } from '../base-view/base-view.component';

@Component({
  selector: 'app-node-view',
  templateUrl: './node-view.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './node-view.component.scss',
  ],
})
export class NodeViewComponent extends BaseViewComponent implements OnInit {
  @Input() node: NodeWithOrg = getEmptyNode();

  constructor(
    protected nodeApiService: NodeApiService,
    protected nodeDataService: NodeDataService,
    public userPermission: UserPermissionService,
    protected modalService: ModalService,
    private http: HttpClient
  ) {
    super(nodeApiService, nodeDataService, modalService);
  }

  getStatus(): string {
    return this.node.is_online ? 'Online' : 'Offline';
  }

  async generateApiKey() {
    let api_key = await this.nodeApiService.reset_api_key(this.node);
    if (api_key) {
      // TODO properly format the command and api key to make them stand out!
      this.modalService.openMessageModal([
        'Your new API key is:',
        api_key,
        `Please paste your new API key into your node configuration file. You
 can find your node configuration file by executing the following command on
 your node machine:`,
        'vnode files',
      ]);
    }
  }

  editNodeName() {
    // open modal window to ask for confirmation of irreversible delete action
    this.modalService
      .openEditModal('name', this.node.name)
      .result.then((data) => {
        if (data.exitMode === ExitMode.EDIT) {
          this.executeEdit(data.new_value);
        }
      });
  }

  executeEdit(edited_value: string) {
    this.node.name = edited_value;
    this.nodeApiService.update(this.node).subscribe(
      (data) => {},
      (error) => {
        this.modalService.openMessageModal([error.error.msg]);
      }
    );
  }

  askConfirmKill() {
    this.modalService
      .openKillModal(
        `You are about to send instructions to stop all tasks running on this node`,
        `all tasks on this node`
      )
      .result.then((exit_mode) => {
        if (exit_mode === ExitMode.KILL) {
          this.kill();
        }
      });
  }

  kill() {
    this.http
      .post<any>(environment.api_url + '/kill/node/tasks', {
        id: this.node.id,
      })
      .subscribe(
        (data: any) => {
          this.modalService.openMessageModal([
            'The node has been instructed to kill its tasks!',
          ]);
        },
        (error: any) => {
          this.modalService.openErrorModal(error.error.msg);
        }
      );
  }
}
