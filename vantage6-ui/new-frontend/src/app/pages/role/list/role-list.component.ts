import { Component, HostBinding, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { SearchRequest } from 'src/app/components/table/table.component';
import { getApiSearchParameters } from 'src/app/helpers/api.helper';
import { unlikeApiParameter } from 'src/app/helpers/general.helper';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { GetRoleParameters } from 'src/app/models/api/role.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { PermissionService } from 'src/app/services/permission.service';
import { RoleService } from 'src/app/services/role.service';

@Component({
  selector: 'app-role-list',
  templateUrl: './role-list.component.html',
  styleUrls: ['./role-list.component.scss']
})
export class RoleListComponent implements OnInit {
  @HostBinding('class') class = 'card-container';

  isLoading: boolean = false;
  canCreate: boolean = false;
  table?: TableData;
  pagination: PaginationLinks | null = null;
  routes = routePaths;
  getRoleParameters: GetRoleParameters = {};
  currentPage: number = 0;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private roleService: RoleService,
    private permissionService: PermissionService
  ) {}

  async ngOnInit(): Promise<void> {
    this.canCreate = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.ROLE, OperationType.CREATE);
    await this.initData(1, this.getRoleParameters);
  }

  private async initData(page: number, getRoleParameters: GetRoleParameters) {
    this.isLoading = true;
    this.currentPage = page;
    await this.getRoles(page, getRoleParameters);
    this.isLoading = false;
  }

  private async getRoles(pageIndex: number, parameters: GetRoleParameters) {
    const result = await this.roleService.getPaginatedRoles(pageIndex, parameters);

    this.table = {
      columns: [
        {
          id: 'name',
          label: this.translateService.instant('role-list.name'),
          searchEnabled: true,
          initSearchString: unlikeApiParameter(this.getRoleParameters.name)
        }
      ],
      rows: result.data.map((role) => ({
        id: role.id.toString(),
        columnData: {
          name: role.name
        }
      }))
    };

    this.pagination = result.links;
  }

  handleTableClick(id: string): void {
    this.router.navigate([routePaths.role, id]);
  }

  handleSearchChanged(searchRequests: SearchRequest[]): void {
    this.getRoleParameters = getApiSearchParameters<GetRoleParameters>(searchRequests);
    this.initData(1, this.getRoleParameters);
  }

  async handlePageEvent(e: PageEvent) {
    await this.initData(e.pageIndex + 1, this.getRoleParameters);
  }
}
