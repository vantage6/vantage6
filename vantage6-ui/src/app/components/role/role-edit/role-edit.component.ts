import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { getEmptyRole, Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { OpsType, ResType } from 'src/app/shared/enum';

import { ApiRoleService } from 'src/app/services/api/api-role.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import { UtilsService } from 'src/app/services/common/utils.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';

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
  rules: Rule[] = [];
  mode: OpsType = OpsType.EDIT;
  organization_id: number | null = null;

  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleService: ApiRoleService,
    private roleDataService: RoleDataService,
    private modalService: ModalService,
    private utilsService: UtilsService,
    private ruleDataService: RuleDataService
  ) {}

  ngOnInit(): void {
    if (this.router.url.includes(OpsType.CREATE)) {
      this.mode = OpsType.CREATE;
    }
    this.init();
  }

  async init(): Promise<void> {
    // subscribe to rule data service to have all rules available
    await this.setRules();

    // subscribe to id parameter in route to change edited role if required
    this.activatedRoute.paramMap.subscribe((params) => {
      if (this.mode !== OpsType.CREATE) {
        let new_id = this.utilsService.getId(params, ResType.ROLE);
        this.setRole(new_id);
      } else {
        this.organization_id = this.utilsService.getId(
          params,
          ResType.ORGANIZATION,
          'org_id'
        );
      }
    });
  }

  async setRole(id: number): Promise<void> {
    this.role = await this.roleDataService.get(id, this.rules);
    // // TODO opern modal if role is empty:
    //   this.modalService.openMessageModal(
    //     ModalMessageComponent,
    //     [error.error.msg],
    //     true
    //   );
  }

  async setRules(): Promise<void> {
    (await this.ruleDataService.list()).subscribe((rules: Rule[]) => {
      this.rules = rules;
    });
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
        if (this.mode === OpsType.CREATE) {
          this.role.id = data.id;
          this.roleDataService.save(this.role);
        }
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
