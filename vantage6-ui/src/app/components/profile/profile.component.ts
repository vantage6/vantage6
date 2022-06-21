import { Component, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { getEmptyUser, User } from 'src/app/interfaces/user';
import { ApiUserService } from 'src/app/services/api/api-user.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { SignOutService } from 'src/app/services/common/sign-out.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { ResType } from 'src/app/shared/enum';
import { Resource } from 'src/app/shared/types';
import { deepcopy } from 'src/app/shared/utils';
import { BaseViewComponent } from '../base/base-view/base-view.component';

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss'],
})
export class ProfileComponent extends BaseViewComponent implements OnInit {
  user: User = getEmptyUser();
  old_password: string = '';

  constructor(
    public userPermission: UserPermissionService,
    protected apiUserService: ApiUserService,
    protected userDataService: UserDataService,
    protected modalService: ModalService,
    private signOutService: SignOutService
  ) {
    super(apiUserService, userDataService, modalService);
  }

  ngOnInit(): void {
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) this.init();
    });
  }

  init(): void {
    this.user = deepcopy(this.userPermission.user);
  }

  signOut() {
    this.signOutService.signOut();
  }

  // TODO implement changing a password when it has been implemented server-side
  savePassword(): void {}
}
