import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import {
  Collaboration,
  EMPTY_COLLABORATION,
} from 'src/app/interfaces/collaboration';
import { Node } from 'src/app/interfaces/node';
import {
  OrganizationInCollaboration,
} from 'src/app/interfaces/organization';
import { ModalService } from 'src/app/services/common/modal.service';
import { UtilsService } from 'src/app/services/common/utils.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { ResType } from 'src/app/shared/enum';
import { BaseSingleViewComponent } from '../base-single-view/base-single-view.component';

@Component({
  selector: 'app-collaboration-view-single',
  templateUrl: './collaboration-view-single.component.html',
  styleUrls: ['./collaboration-view-single.component.scss'],
})
export class CollaborationViewSingleComponent
  extends BaseSingleViewComponent
  implements OnInit
{
  organizations: OrganizationInCollaboration[] = [];
  nodes: Node[] = [];
  collaboration: Collaboration = EMPTY_COLLABORATION;

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private collabDataService: CollabDataService,
    protected utilsService: UtilsService,
    protected modalService: ModalService
  ) {
    super(
      activatedRoute,
      userPermission,
      utilsService,
      ResType.COLLABORATION,
      modalService
    );
  }

  async setResources() {
    this.setCollaboration();
  }

  async setCollaboration(): Promise<void> {
    (await this.collabDataService.get(this.route_id as number, true)).subscribe(
      (collab) => {
        this.collaboration = collab;
      }
    );
  }
}
