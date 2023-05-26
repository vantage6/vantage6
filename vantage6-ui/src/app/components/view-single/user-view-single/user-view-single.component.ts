import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { EMPTY_USER, User } from 'src/app/interfaces/user';
import { ModalService } from 'src/app/services/common/modal.service';
import { UtilsService } from 'src/app/services/common/utils.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { ResType } from 'src/app/shared/enum';
import { BaseSingleViewComponent } from '../base-single-view/base-single-view.component';

@Component({
  selector: 'app-user-view-single',
  templateUrl: './user-view-single.component.html',
  styleUrls: ['./user-view-single.component.scss'],
})
export class UserViewSingleComponent
  extends BaseSingleViewComponent
  implements OnInit
{
  user: User = EMPTY_USER;

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private userDataService: UserDataService,
    protected utilsService: UtilsService,
    protected modalService: ModalService,
    private orgDataService: OrgDataService
  ) {
    console.log('UserViewSingleComponent');
    super(
      activatedRoute,
      userPermission,
      utilsService,
      ResType.USER,
      modalService
    );
  }

  async setResources() {
    await this.setUser();

    await this.setOrganization();
  }

  async setUser() {
    (
      await this.userDataService.get(this.route_id as number, true)
    ).subscribe((user) => {
      this.user = user;
    });
  }

  async setOrganization() {
    if (this.user)
      (await this.orgDataService.get(this.user.organization_id)).subscribe(
        (org) => {
          this.user.organization = org;
        }
      );
  }
}
