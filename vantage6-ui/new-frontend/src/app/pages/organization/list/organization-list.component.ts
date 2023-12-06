import { Component, HostBinding, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { OrganizationService } from 'src/app/services/organization.service';
import { PermissionService } from 'src/app/services/permission.service';

@Component({
  selector: 'app-organization-list',
  templateUrl: './organization-list.component.html'
})
export class OrganizationListComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  routes = routePaths;

  isLoading: boolean = true;
  canCreate: boolean = false;
  table?: TableData;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private organizationService: OrganizationService,
    private permissionService: PermissionService
  ) {}

  async ngOnInit(): Promise<void> {
    this.canCreate = this.permissionService.isAllowed(ScopeType.GLOBAL, ResourceType.ORGANIZATION, OperationType.CREATE);
    await this.initData();
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getOrganizations();
  }

  handleTableClick(id: string): void {
    this.router.navigate([routePaths.organization, id]);
  }

  private async initData() {
    await this.getOrganizations();
    this.isLoading = false;
  }

  private async getOrganizations() {
    const result = await this.organizationService.getPaginatedOrganizations(this.currentPage, { sort: OrganizationSortProperties.Name });

    this.table = {
      columns: [
        { id: 'name', label: this.translateService.instant('organization.name') },
        { id: 'country', label: this.translateService.instant('organization.country') }
      ],
      rows: result.data.map((_) => ({ id: _.id.toString(), columnData: { name: _.name, country: _.country } }))
    };
    this.pagination = result.links;
  }
}
