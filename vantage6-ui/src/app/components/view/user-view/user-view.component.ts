import { Component, Input, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { EMPTY_USER, getEmptyUser, User } from 'src/app/interfaces/user';
import { UserApiService } from 'src/app/services/api/user-api.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { ResType } from 'src/app/shared/enum';
import { BaseViewComponent } from '../base-view/base-view.component';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { allPages } from 'src/app/interfaces/utils';
import { getIdsFromArray, removeMatchedIdsFromArray } from 'src/app/shared/utils';

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
    protected modalService: ModalService,
    private ruleDataService: RuleDataService,
    private roleDataService: RoleDataService
  ) {
    super(userApiService, userDataService, modalService);
    this.setUp();
  }

  ngOnChanges(): void {
    this.setUp();
  }

  private async setUp(): Promise<void> {
    if (this.user.id !== EMPTY_USER.id) {
      await this.addRoles();
      this.addRules();
    }
  }

  private async addRoles(): Promise<void> {
    this.user.roles = await this.roleDataService.list_with_params(
      allPages(),
      { user_id: this.user.id },
      true
    );
  }

  private async addRules(): Promise<void> {
    let rules = await this.ruleDataService.list_with_params(
      allPages(),
      { user_id: this.user.id }
    );
    // remove rules that are already in roles
    for (let role of this.user.roles) {
      rules = removeMatchedIdsFromArray(rules, getIdsFromArray(role.rules));
    }
    this.user.rules = rules;
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
