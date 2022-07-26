import { Component, Input, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { getEmptyUser, User } from 'src/app/interfaces/user';
import { UserApiService } from 'src/app/services/api/api-user.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { ResType } from 'src/app/shared/enum';
import { BaseViewComponent } from '../../base/base-view/base-view.component';

@Component({
  selector: 'app-user-view',
  templateUrl: './user-view.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './user-view.component.scss',
  ],
})
export class UserViewComponent extends BaseViewComponent implements OnInit {
  @Input() user: User = getEmptyUser();

  constructor(
    public userPermission: UserPermissionService,
    protected userApiService: UserApiService,
    protected userDataService: UserDataService,
    protected modalService: ModalService
  ) {
    super(userApiService, userDataService, modalService);
  }

  askConfirmDelete(): void {
    let message = '';
    if (this.user.id === this.userPermission.user.id) {
      message =
        'This is your own account! You will be logged out if you delete it.';
    }
    super.askConfirmDelete(this.user, ResType.USER, message);
  }
}
