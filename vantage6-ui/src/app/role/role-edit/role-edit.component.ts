import { Component, OnInit } from '@angular/core';
import { Location } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';

import { getEmptyRole, Role } from 'src/app/interfaces/role';
import { Operation, Rule } from 'src/app/interfaces/rule';

import { RoleService } from 'src/app/services/api/role.service';
import { UserPermissionService } from 'src/app/services/user-permission.service';
import { RoleEditService } from '../role-edit.service';
import { ModalService } from 'src/app/modal/modal.service';
import { ModalMessageComponent } from 'src/app/modal/modal-message/modal-message.component';
import { UtilsService } from 'src/app/services/utils.service';

@Component({
  selector: 'app-role-edit',
  templateUrl: './role-edit.component.html',
  styleUrls: ['../../globals/buttons.scss', './role-edit.component.scss'],
})
export class RoleEditComponent implements OnInit {
  role: Role = getEmptyRole();
  id: number = this.role.id;
  mode: Operation = Operation.EDIT;

  constructor(
    private location: Location,
    private router: Router,
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleService: RoleService,
    private roleEditService: RoleEditService,
    private modalService: ModalService,
    private utilsService: UtilsService
  ) {}

  ngOnInit(): void {
    this.roleEditService.getRole().subscribe((role) => {
      this.role = role;
    });
    if (this.router.url.endsWith('create')) {
      this.mode = Operation.CREATE;
    }
    // subscribe to id parameter in route to change edited role if required
    this.activatedRoute.paramMap.subscribe((params) => {
      let new_id = this.utilsService.getId(params, 'role');
      if (new_id !== this.id) {
        this.id = new_id;
        this.setRoleFromAPI(new_id);
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
    let request;
    if (this.mode === Operation.CREATE) {
      request = this.roleService.create(this.role);
    } else {
      request = this.roleService.update(this.role);
    }

    request.subscribe(
      (data) => {
        this.goBack();
      },
      (error) => {
        alert(error.error.msg);
      }
    );
  }

  cancelEdit(): void {
    this.goBack();
  }

  updateAddedRules($event: Rule[]) {
    this.role.rules = $event;
  }

  goBack(): void {
    // go back to previous page
    this.location.back();
  }

  isCreate(): boolean {
    return this.mode === Operation.CREATE;
  }
}
