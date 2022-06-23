import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { EMPTY_USER, User } from 'src/app/interfaces/user';
import { UtilsService } from 'src/app/services/common/utils.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { ResType } from 'src/app/shared/enum';
import { BaseSingleViewComponent } from '../../base/base-single-view/base-single-view.component';

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
  roles: Role[] = [];
  rules: Rule[] = [];

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    private userDataService: UserDataService,
    protected utilsService: UtilsService
  ) {
    super(activatedRoute, userPermission, utilsService, ResType.USER);
  }

  async setResources() {
    // TODO organize this in a different way: first get the collaboration, then
    // get ONLY the organizations and nodes relevant for that collab, instead
    // of all of them first and then getting single collaboration
    await this.setRules();

    await this.setRoles();

    this.setUser();
  }

  async setRules() {
    (await this.ruleDataService.list()).subscribe((rules) => {
      this.rules = rules;
    });
  }

  async setRoles() {
    this.roles = await this.roleDataService.list_with_params(this.rules, {
      user_id: this.route_id,
    });
  }

  async setUser() {
    this.user = await this.userDataService.get(
      this.route_id as number,
      this.roles,
      this.rules
    );
  }
}
