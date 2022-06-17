import { AfterViewInit, Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Role, RoleWithOrg } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { TableComponent } from 'src/app/components/base/table/table.component';

@Component({
  selector: 'app-role-table',
  templateUrl: './role-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../base/table/table.component.scss',
    './role-table.component.scss',
  ],
})
export class RoleTableComponent
  extends TableComponent
  implements OnInit, AfterViewInit
{
  rules: Rule[] = [];
  show_default_roles: boolean = true;
  roles_without_defaults: Role[] = [];

  displayedColumns: string[] = ['name', 'organization', 'description'];

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    private orgDataService: OrgDataService
  ) {
    super(activatedRoute, userPermission);
  }

  ngAfterViewInit(): void {
    super.ngAfterViewInit();
    this.table_data.sortingDataAccessor = (item: any, property: any) => {
      let sorter: any;
      if (property === 'organization') {
        sorter = item.organization ? item.organization.name : '';
      } else {
        sorter = item[property];
      }
      return sorter ? sorter.toLocaleLowerCase() : '';
    };
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

  toggleDefaultRoles(): void {
    this.show_default_roles = !this.show_default_roles;
    if (this.show_default_roles) {
      this.table_data.data = this.resources;
    } else {
      this.roles_without_defaults = this.resources.filter(function (elem: any) {
        return elem.organization_id !== null;
      }) as Role[];
      this.table_data.data = this.roles_without_defaults;
    }
  }
}
