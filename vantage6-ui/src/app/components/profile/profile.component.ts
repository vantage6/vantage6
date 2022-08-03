import { Component, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { getEmptyUser, User } from 'src/app/interfaces/user';
import { UserApiService } from 'src/app/services/api/user-api.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { SignOutService } from 'src/app/services/common/sign-out.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { ResType } from 'src/app/shared/enum';
import { Resource } from 'src/app/shared/types';
import { deepcopy } from 'src/app/shared/utils';
import { BaseViewComponent } from '../view/base-view/base-view.component';
import { ModalMessageComponent } from '../modal/modal-message/modal-message.component';
import { OrgDataService } from 'src/app/services/data/org-data.service';

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
  styleUrls: ['../../shared/scss/buttons.scss', './profile.component.scss'],
})
export class ProfileComponent extends BaseViewComponent implements OnInit {
  user: User = getEmptyUser();
  old_password: string = '';
  new_password: string = '';
  new_password_repeated: string = '';

  constructor(
    public userPermission: UserPermissionService,
    protected userApiService: UserApiService,
    protected userDataService: UserDataService,
    protected modalService: ModalService,
    private signOutService: SignOutService,
    private orgDataService: OrgDataService
  ) {
    super(userApiService, userDataService, modalService);
  }

  ngOnInit(): void {
    this.modalService.openLoadingModal();
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) this.init();
    });
  }

  async init(): Promise<void> {
    this.user = deepcopy(this.userPermission.user);
    this.user.organization = await this.orgDataService.get(
      this.user.organization_id
    );
    this.modalService.closeLoadingModal();
  }

  signOut() {
    this.signOutService.signOut();
  }

  hasFilledInPasswords(): boolean {
    return (
      this.old_password.length > 0 &&
      this.new_password.length > 0 &&
      this.new_password === this.new_password_repeated
    );
  }

  // TODO implement changing a password when it has been implemented server-side
  async savePassword(): Promise<void> {
    this.userApiService
      .change_password(this.old_password, this.new_password)
      .subscribe(
        (data: any) => {
          this.modalService.openMessageModal(ModalMessageComponent, [
            'Your password was changed successfully!',
          ]);
          this.old_password = '';
          this.new_password = '';
          this.new_password_repeated = '';
        },
        (error: any) => {
          this.modalService.openMessageModal(ModalMessageComponent, [
            error.error.msg,
          ]);
        }
      );
  }
}
