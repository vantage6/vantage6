import { Component, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { getEmptyUser, User } from 'src/app/interfaces/user';
import { UserApiService } from 'src/app/services/api/user-api.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { SignOutService } from 'src/app/services/common/sign-out.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { deepcopy } from 'src/app/shared/utils';
import { BaseViewComponent } from '../view/base-view/base-view.component';
import { OrgDataService } from 'src/app/services/data/org-data.service';

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
  styleUrls: ['../../shared/scss/buttons.scss', './profile.component.scss'],
})
export class ProfileComponent extends BaseViewComponent implements OnInit {
  user: User = getEmptyUser();

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
    (await this.orgDataService.get(this.user.organization_id)).subscribe(
      (org) => {
        this.user.organization = org;
      }
    );
    this.modalService.closeLoadingModal();
  }

  signOut() {
    this.signOutService.signOut();
  }
}
