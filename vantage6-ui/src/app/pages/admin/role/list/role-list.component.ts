import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { PageEvent, MatPaginator } from '@angular/material/paginator';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { BaseListComponent } from 'src/app/components/admin-base/base-list/base-list.component';
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
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatCard, MatCardContent } from '@angular/material/card';
import { TableComponent } from '../../../../components/table/table.component';

@Component({
  selector: 'app-role-list',
  templateUrl: './role-list.component.html',
  styleUrls: ['./role-list.component.scss'],
  standalone: true,
  imports: [
    PageHeaderComponent,
    NgIf,
    MatButton,
    RouterLink,
    MatIcon,
    MatCard,
    MatCardContent,
    TableComponent,
    MatPaginator,
    TranslateModule
  ]
})
export class RoleListComponent extends BaseListComponent implements OnInit, OnDestroy {
  getRoleParameters: GetRoleParameters = {};

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private roleService: RoleService,
    private permissionService: PermissionService
  ) {
    super();
  }

  async ngOnInit(): Promise<void> {
    this.setPermissions();
    await this.initData(1, {});
  }

  protected async initData(page: number, parameters: GetRoleParameters) {
    this.isLoading = true;
    this.currentPage = page;
    this.getRoleParameters = parameters;
    await this.getRoles(page, parameters);
    this.isLoading = false;
  }

  private async getRoles(pageIndex: number, parameters: GetRoleParameters) {
    const result = await this.roleService.getPaginatedRoles(pageIndex, parameters);

    this.table = {
      columns: [
        { id: 'id', label: this.translateService.instant('general.id') },
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
          id: role.id,
          name: role.name
        }
      }))
    };

    this.pagination = result.links;
  }

  handleTableClick(id: string): void {
    this.router.navigate([routePaths.role, id]);
  }

  async handlePageEvent(e: PageEvent) {
    await this.initData(e.pageIndex + 1, this.getRoleParameters);
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canCreate = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.ROLE, OperationType.CREATE);
        }
      });
  }
}
