import { Component, HostBinding, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
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

  isLoading: boolean = true;
  canCreate: boolean = false;
  table?: TableData;
  pagination: PaginationLinks | null = null;
  routes = routePaths;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private roleService: RoleService,
    private permissionService: PermissionService
  ) {}

  async ngOnInit(): Promise<void> {
    this.canCreate = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.ROLE, OperationType.CREATE);
    await this.initData();
  }

  private async initData() {
    await this.getRoles(1);
    this.isLoading = false;
  }

  private async getRoles(pageIndex: number) {
    const result = await this.roleService.getPaginatedRoles(pageIndex);

    this.table = {
      columns: [{ id: 'name', label: this.translateService.instant('role-list.name') }],
      rows: result.data.map((_) => ({
        id: _.id.toString(),
        columnData: {
          name: _.name
        }
      }))
    };

    this.pagination = result.links;
  }

  handleTableClick(id: string): void {
    this.router.navigate([routePaths.role, id]);
  }

  async handlePageEvent(e: PageEvent) {
    await this.getRoles(e.pageIndex + 1);
  }
}
