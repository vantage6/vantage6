import { Component, Input, OnChanges, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { EMPTY_ROLE, getEmptyRole, RoleWithOrg } from 'src/app/interfaces/role';
import { User } from 'src/app/interfaces/user';
import { allPages } from 'src/app/interfaces/utils';
import { RoleApiService } from 'src/app/services/api/role-api.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { ResType } from 'src/app/shared/enum';
import { BaseViewComponent } from '../base-view/base-view.component';

@Component({
  selector: 'app-role-view',
  templateUrl: './role-view.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './role-view.component.scss',
  ],
})
export class RoleViewComponent
  extends BaseViewComponent
  implements OnInit, OnChanges
{
  @Input() role: RoleWithOrg = getEmptyRole();
  users_with_this_role: User[] = [];

  constructor(
    public userPermission: UserPermissionService,
    protected roleApiService: RoleApiService,
    protected roleDataService: RoleDataService,
    protected modalService: ModalService,
    private userDataService: UserDataService,
    private ruleDataService: RuleDataService,
  ) {
    super(roleApiService, roleDataService, modalService);
  }

  ngOnChanges() {
    if (this.role.id !== EMPTY_ROLE.id) {
      this.setUsers();
      this.setRules();
    }
  }

  async setUsers(): Promise<void> {
    (await this.userDataService.list_with_params(
      {
        role_id: this.role.id,
      }
    )).subscribe((users) => {
      this.users_with_this_role = users;
    });
  }

  async setRules(): Promise<void> {
    (await this.ruleDataService.list_with_params(
      allPages(), {role_id: this.role.id}
    )).subscribe((rules) => {
      this.role.rules = rules;

      // renew role object to trigger ngOnChange detection in child components
      this.role = {...this.role};
    });
  }

  isDefaultRole(): boolean {
    return this.roleDataService.isDefaultRole(this.role);
  }

  async delete(): Promise<void> {
    super.delete(this.role, {delete_dependents: true});
  }

  askConfirmDelete(): void {
    super.askConfirmDelete(
      this.role,
      ResType.ROLE,
      'This role will also be deleted from any users that possess this role.'
    );
  }

  getUserNameText(user: User): string {
    return user.first_name
      ? `${user.first_name} ${user.last_name}`
      : user.username;
  }
}
