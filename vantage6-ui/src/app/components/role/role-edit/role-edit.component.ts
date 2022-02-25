import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { getEmptyRole, Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { OpsType, ResType } from 'src/app/shared/enum';

import { ApiRoleService } from 'src/app/services/api/api-role.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { RoleStoreService } from 'src/app/services/store/role-store.service';
import { ModalService } from 'src/app/modal/modal.service';
import { ModalMessageComponent } from 'src/app/modal/modal-message/modal-message.component';
import { UtilsService } from 'src/app/shared/services/utils.service';
import { PermissionTableComponent } from '../../permission-table/permission-table.component';

@Component({
  selector: 'app-role-edit',
  templateUrl: './role-edit.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './role-edit.component.scss',
  ],
})
export class RoleEditComponent implements OnInit {
  role: Role = getEmptyRole();
  id: number = this.role.id;
  mode: OpsType = OpsType.EDIT;
  organization_id: number | null = null;

  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleService: ApiRoleService,
    private roleStoreService: RoleStoreService,
    private modalService: ModalService,
    private utilsService: UtilsService
  ) {}

  ngOnInit(): void {
    this.roleStoreService.getRole().subscribe((role) => {
      this.role = role;
    });
    if (this.router.url.includes(OpsType.CREATE)) {
      this.mode = OpsType.CREATE;
    }
    // subscribe to id parameter in route to change edited role if required
    this.activatedRoute.paramMap.subscribe((params) => {
      if (this.mode !== OpsType.CREATE) {
        let new_id = this.utilsService.getId(params, ResType.ROLE);
        if (new_id !== this.id) {
          this.id = new_id;
          this.setRoleFromAPI(new_id);
        }
      } else {
        this.organization_id = this.utilsService.getId(
          params,
          ResType.ORGANIZATION,
          'org_id'
        );
      }
    });
  }

  async setRoleFromAPI(id: number): Promise<void> {
    try {
      this.role = await this.roleService.getRole(id);
    } catch (error: any) {
      this.modalService.openMessageModal(
        ModalMessageComponent,
        [error.error.msg],
        true
      );
    }
  }

  saveEdit(): void {
    if (this.role.rules.length === 0) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'You have not selected any permissions! Please select at least one permission.',
      ]);
      return;
    }

    if (this.organization_id) this.role.organization_id = this.organization_id;

    let request;
    if (this.mode === OpsType.CREATE) {
      request = this.roleService.create(this.role);
    } else {
      request = this.roleService.update(this.role);
    }

    request.subscribe(
      (data) => {
        this.utilsService.goToPreviousPage();
      },
      (error) => {
        this.modalService.openMessageModal(ModalMessageComponent, [
          error.error.msg,
        ]);
      }
    );
  }

  cancelEdit(): void {
    this.utilsService.goToPreviousPage();
  }

  updateAddedRules($event: Rule[]) {
    this.role.rules = $event;
  }

  isCreate(): boolean {
    return this.mode === OpsType.CREATE;
  }
}
