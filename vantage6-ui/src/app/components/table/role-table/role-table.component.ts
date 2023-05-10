import { AfterViewInit, Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Role, RoleWithOrg } from 'src/app/interfaces/role';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { TableComponent } from 'src/app/components/table/base-table/table.component';
import { ModalService } from 'src/app/services/common/modal.service';
import {
  Pagination,
  allPages,
  defaultFirstPage,
} from 'src/app/interfaces/utils';
import { RoleApiService } from 'src/app/services/api/role-api.service';

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
  show_default_roles: boolean = true;
  roles_without_defaults: RoleWithOrg[] = [];

  displayedColumns: string[] = ['id', 'name', 'organization', 'description'];

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleDataService: RoleDataService,
    private orgDataService: OrgDataService,
    protected modalService: ModalService
  ) {
    super(activatedRoute, userPermission, modalService, roleDataService);
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
    // get organizations
    (await this.orgDataService.list(false, allPages())).subscribe((orgs) => {
      this.organizations = orgs;
      this.addOrgsToRoles();
    });

    this.readRoute();
  }

  protected async setResources(
    force_refresh: boolean = false,
    pagination: Pagination = defaultFirstPage()
  ): Promise<void> {
    // TODO update other things when resources are updated?
    if (this.isShowingSingleOrg()) {
      (
        await this.roleDataService.org_list(
          this.route_org_id as number,
          force_refresh,
          pagination
        )
      ).subscribe((roles) => {
        this.resources = roles;
      });
    } else {
      (await this.roleDataService.list(force_refresh, pagination)).subscribe(
        (roles: Role[]) => {
          this.resources = roles;
        }
      );
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

  addOrgsToRoles(): void {
    for (let role of this.roles_without_defaults) {
      for (let org of this.organizations) {
        if (role.organization_id === org.id) {
          role.organization = org;
        }
      }
    }
  }
}
