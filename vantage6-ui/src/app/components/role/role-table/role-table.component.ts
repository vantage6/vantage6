import { AfterViewInit, Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { EMPTY_USER, User } from 'src/app/interfaces/user';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { TableComponent } from 'src/app/components/table/table.component';

@Component({
  selector: 'app-role-table',
  templateUrl: './role-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../table/table.component.scss',
    './role-table.component.scss',
  ],
})
export class RoleTableComponent
  extends TableComponent
  implements OnInit, AfterViewInit
{
  rules: Rule[] = [];

  displayedColumns: string[] = ['name', 'organization', 'descr'];

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    private orgDataService: OrgDataService
  ) {
    super(activatedRoute, userPermission);
  }

  async init(): Promise<void> {
    // get rules
    (await this.ruleDataService.list()).subscribe((rules) => {
      this.rules = rules;
    });

    // get organizations
    (await this.orgDataService.list()).subscribe((orgs) => {
      this.organizations = orgs;
    });

    this.readRoute();
  }

  protected async setResources() {
    if (this.isShowingSingleOrg()) {
      this.resources = await this.roleDataService.org_list(
        this.route_org_id as number,
        this.rules
      );
    } else {
      (await this.roleDataService.list(this.rules)).subscribe(
        (roles: Role[]) => {
          this.resources = roles;
        }
      );
    }
  }
}
