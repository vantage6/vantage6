import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { ExitMode, ResType } from 'src/app/shared/enum';

import { Role, getEmptyRole } from 'src/app/interfaces/role';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import { ModalService } from 'src/app/services/common/modal.service';

import { ApiRoleService } from 'src/app/services/api/api-role.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';

@Component({
  selector: 'app-role-view',
  templateUrl: './role-view.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './role-view.component.scss',
  ],
})
export class RoleViewComponent implements OnInit {
  @Input() role: Role = getEmptyRole();
  @Output() deletingRole = new EventEmitter<Role>();

  constructor(
    public userPermission: UserPermissionService,
    public roleService: ApiRoleService,
    private roleDataService: RoleDataService,
    private modalService: ModalService
  ) {}

  ngOnInit(): void {}

  executeDelete(): void {
    this.roleService.delete(this.role).subscribe(
      (data) => {
        this.deletingRole.emit(this.role);
      },
      (error) => {
        this.modalService.openMessageModal(ModalMessageComponent, [
          error.error.msg,
        ]);
      }
    );
  }

  deleteRole(): void {
    // open modal window to ask for confirmation of irreversible delete action
    this.modalService
      .openDeleteModal(
        this.role,
        ResType.ROLE,
        'This role will also be deleted from any users that possess this role.'
      )
      .result.then((exit_mode) => {
        if (exit_mode === ExitMode.DELETE) {
          this.executeDelete();
        }
      });
  }

  editRole(): void {
    this.roleDataService.save(this.role);
  }

  isDefaultRole(role: Role): boolean {
    return role.organization_id === null;
  }
}
