import { AfterViewInit, Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Role, RoleWithOrg } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { TableComponent } from 'src/app/components/table/base-table/table.component';
import { ModalService } from 'src/app/services/common/modal.service';

@Component({
  selector: 'app-role-table',
  templateUrl: './role-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../table/base-table/table.component.scss',
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

  displayedColumns: string[] = ['id', 'name', 'organization', 'description'];

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    private orgDataService: OrgDataService,
    protected modalService: ModalService
  ) {
    super(activatedRoute, userPermission, modalService);
  }

  ngAfterViewInit(): void {
    super.ngAfterViewInit();
    this.dataSource.sortingDataAccessor = (item: any, property: any) => {
      let sorter: any;
      if (property === 'organization') {
        sorter = item.organization ? item.organization.name : '';
      } else {
        sorter = item[property];
      }
      return this.sortBy(sorter);
    };
  }

  async init(): Promise<void> {
    // get rules
    this.rules = await this.ruleDataService.list();

    // get organizations
    this.organizations = await this.orgDataService.list();

    this.readRoute();
  }

  protected async setResources() {
    if (this.isShowingSingleOrg()) {
      this.resources = await this.roleDataService.org_list(
        this.route_org_id as number,
        this.rules
      );
    } else {
      this.resources = await this.roleDataService.list(this.rules);
    }
  }

  toggleDefaultRoles(): void {
    this.show_default_roles = !this.show_default_roles;
    if (this.show_default_roles) {
      this.dataSource.data = this.resources;
    } else {
      this.roles_without_defaults = this.resources.filter(function (elem: any) {
        return elem.organization_id !== null;
      }) as Role[];
      this.dataSource.data = this.roles_without_defaults;
    }
  }
}
