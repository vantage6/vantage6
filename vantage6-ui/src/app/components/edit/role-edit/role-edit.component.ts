import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { getEmptyRole, Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { OpsType, ResType } from 'src/app/shared/enum';

import { RoleApiService } from 'src/app/services/api/role-api.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import { UtilsService } from 'src/app/services/common/utils.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { BaseEditComponent } from '../base-edit/base-edit.component';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { Organization } from 'src/app/interfaces/organization';

@Component({
  selector: 'app-role-edit',
  templateUrl: './role-edit.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './role-edit.component.scss',
  ],
})
export class RoleEditComponent extends BaseEditComponent implements OnInit {
  rules: Rule[] = [];
  mode: OpsType = OpsType.EDIT;
  role: Role = getEmptyRole();
  role_orig_name: string = '';

  constructor(
    protected router: Router,
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    protected RoleApiService: RoleApiService,
    protected roleDataService: RoleDataService,
    protected modalService: ModalService,
    protected utilsService: UtilsService,
    private ruleDataService: RuleDataService,
    private orgDataService: OrgDataService
  ) {
    super(
      router,
      activatedRoute,
      userPermission,
      utilsService,
      RoleApiService,
      roleDataService,
      modalService
    );
  }

  async init(): Promise<void> {
    // subscribe to rule data service to have all rules available
    await this.setRules();

    // subscribe to id parameter in route to change edited role if required
    this.readRoute();
  }

  async setupCreate() {
    if (!this.organization_id) {
      this.organizations = await this.orgDataService.list();
    }
  }

  async setupEdit(id: number): Promise<void> {
    let role = await this.roleDataService.get(id, this.rules);
    if (role) {
      this.role = role;
      this.role_orig_name = this.role.name;
    }
  }

  async setRules(): Promise<void> {
    this.rules = await this.ruleDataService.list();
  }

  async save(): Promise<void> {
    if (this.role.rules.length === 0) {
      this.modalService.openMessageModal([
        'You have not selected any permissions! Please select at least one permission.',
      ]);
      return;
    }
    if (this.organization_id) this.role.organization_id = this.organization_id;

    super.save(this.role);
  }

  updateAddedRules($event: Rule[]) {
    this.role.rules = $event;
  }

  getTitle(): string {
    return this.mode === OpsType.EDIT
      ? `Edit role '${this.role_orig_name}'`
      : 'Create a new role';
  }
}
