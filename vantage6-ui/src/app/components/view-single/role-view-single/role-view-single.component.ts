import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { EMPTY_ROLE, Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { ModalService } from 'src/app/services/common/modal.service';
import { UtilsService } from 'src/app/services/common/utils.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { ResType } from 'src/app/shared/enum';
import { BaseSingleViewComponent } from '../base-single-view/base-single-view.component';

@Component({
  selector: 'app-role-view-single',
  templateUrl: './role-view-single.component.html',
  styleUrls: ['./role-view-single.component.scss'],
})
export class RoleViewSingleComponent
  extends BaseSingleViewComponent
  implements OnInit
{
  role: Role = EMPTY_ROLE;
  rules: Rule[] = [];

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    protected utilsService: UtilsService,
    protected modalService: ModalService
  ) {
    super(
      activatedRoute,
      userPermission,
      utilsService,
      ResType.ROLE,
      modalService
    );
  }

  async init() {
    (await this.ruleDataService.list()).subscribe((rules) => {
      this.rules = rules;
    });

    this.readRoute();
  }

  async setResources(): Promise<void> {
    (await this.roleDataService.get(this.route_id as number)).subscribe(
      (role) => {
        this.role = role;
      }
    );
  }
}
