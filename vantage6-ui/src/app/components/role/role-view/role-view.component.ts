import { Component, Input, OnInit } from '@angular/core';
import { ResType } from 'src/app/shared/enum';

import { getEmptyRole, Role } from 'src/app/interfaces/role';
import { ModalService } from 'src/app/services/common/modal.service';

import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ApiRoleService } from 'src/app/services/api/api-role.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { BaseViewComponent } from '../../base/base-view/base-view.component';

@Component({
  selector: 'app-role-view',
  templateUrl: './role-view.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './role-view.component.scss',
  ],
})
export class RoleViewComponent extends BaseViewComponent implements OnInit {
  @Input() role: Role = getEmptyRole();

  constructor(
    public userPermission: UserPermissionService,
    protected apiRoleService: ApiRoleService,
    protected roleDataService: RoleDataService,
    protected modalService: ModalService
  ) {
    super(apiRoleService, roleDataService, modalService);
  }

  isDefaultRole(): boolean {
    return this.roleDataService.isDefaultRole(this.role);
  }

  askConfirmDelete(): void {
    super.askConfirmDelete(
      this.role,
      ResType.ROLE,
      'This role will also be deleted from any users that possess this role.'
    );
  }
}
