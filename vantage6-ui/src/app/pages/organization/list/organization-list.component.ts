import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { SearchRequest } from 'src/app/components/table/table.component';
import { getApiSearchParameters } from 'src/app/helpers/api.helper';
import { unlikeApiParameter } from 'src/app/helpers/general.helper';
import { GetOrganizationParameters, OrganizationSortProperties } from 'src/app/models/api/organization.model';
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
export class OrganizationListComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  routes = routePaths;
  destroy$ = new Subject();

  isLoading: boolean = false;
  canCreate: boolean = false;
  table?: TableData;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;
  getOrganizationParameters: GetOrganizationParameters = {};

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private organizationService: OrganizationService,
    private permissionService: PermissionService
  ) {}

  async ngOnInit(): Promise<void> {
    this.setPermissions();
    await this.initData(1, {});
  }

  async ngOnDestroy(): Promise<void> {
    this.destroy$.next(true);
  }

  async handlePageEvent(e: PageEvent) {
    await this.initData(e.pageIndex + 1, this.getOrganizationParameters);
  }

  handleTableClick(id: string): void {
    this.router.navigate([routePaths.organization, id]);
  }

  private async initData(page: number, parameters: GetOrganizationParameters) {
    this.isLoading = true;
    this.currentPage = page;
    this.getOrganizationParameters = parameters;
    const getParameters = { ...parameters, sort: OrganizationSortProperties.Name };
    await this.getOrganizations(page, getParameters);
    this.isLoading = false;
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canCreate = this.permissionService.isAllowed(ScopeType.GLOBAL, ResourceType.ORGANIZATION, OperationType.CREATE);
        }
      });
  }

  private async getOrganizations(page: number, parameters: GetOrganizationParameters) {
    const result = await this.organizationService.getPaginatedOrganizations(page, parameters);

    this.table = {
      columns: [
        { id: 'id', label: this.translateService.instant('general.id') },
        {
          id: 'name',
          label: this.translateService.instant('organization.name'),
          searchEnabled: true,
          initSearchString: unlikeApiParameter(parameters.name)
        },
        { id: 'country', label: this.translateService.instant('organization.country') }
      ],
      rows: result.data.map((_) => ({ id: _.id.toString(), columnData: { id: _.id, name: _.name, country: _.country } }))
    };
    this.pagination = result.links;
  }

  public handleSearchChanged(searchRequests: SearchRequest[]): void {
    const parameters = getApiSearchParameters<GetOrganizationParameters>(searchRequests);
    this.initData(1, parameters);
  }
}
