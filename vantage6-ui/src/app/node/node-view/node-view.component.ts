import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { take } from 'rxjs/operators';

import { EMPTY_NODE, Node } from '../interfaces/node';
import { ModalMessageComponent } from 'src/app/modal/modal-message/modal-message.component';
import { ResType } from 'src/app/shared/enum';

import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ModalService } from 'src/app/modal/modal.service';
import { UtilsService } from 'src/app/shared/services/utils.service';
import { ApiNodeService } from '../services/api-node.service';
import { NodeEditService } from '../services/node-edit.service';

@Component({
  selector: 'app-node-view',
  templateUrl: './node-view.component.html',
  styleUrls: ['../../shared/scss/buttons.scss', './node-view.component.scss'],
})
export class NodeViewComponent implements OnInit {
  node: Node = EMPTY_NODE;
  id: number = -1;

  constructor(
    private activatedRoute: ActivatedRoute,
    private apiNodeService: ApiNodeService,
    private nodeEditService: NodeEditService,
    private utilsService: UtilsService,
    public userPermission: UserPermissionService,
    private modalService: ModalService
  ) {}

  ngOnInit(): void {
    this.init();
  }

  async init(): Promise<void> {
    // try to see if organization is already passed from organizationEditService
    this.nodeEditService
      .getNode()
      .pipe(take(1))
      .subscribe((node) => {
        this.node = node;
        this.id = this.node.id;
      });

    // subscribe to id parameter in route to change edited organization if
    // required
    this.activatedRoute.paramMap.subscribe((params) => {
      let new_id = this.utilsService.getId(params, ResType.NODE);
      if (new_id === EMPTY_NODE.id) {
        return; // cannot get organization
      }
      if (new_id !== this.id) {
        this.id = new_id;
        this.setNodeFromAPI(new_id);
      }
    });
  }

  async setNodeFromAPI(id: number): Promise<void> {
    this.node = await this.apiNodeService.getNode(id);
  }

  getStatus(): string {
    return this.node.is_online ? 'Online' : 'Offline';
  }

  async generateApiKey() {
    let api_key = await this.apiNodeService.reset_api_key(this.node);
    if (api_key) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'Your new API key is:',
        api_key,
      ]);
    }
  }
}
