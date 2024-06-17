import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { SearchRequest } from 'src/app/components/table/table.component';
import { getApiSearchParameters } from 'src/app/helpers/api.helper';
import { unlikeApiParameter } from 'src/app/helpers/general.helper';
import { CollaborationSortProperties, GetCollaborationParameters } from 'src/app/models/api/collaboration.model';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';

@Component({
  selector: 'app-collaboration-list',
  templateUrl: './collaboration-list.component.html'
})
export class CollaborationListComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  routes = routePaths;
  destroy$ = new Subject();

  isLoading: boolean = false;
  canCreate: boolean = false;
  table?: TableData;
  pagination: PaginationLinks | null = null;
  currentPage: number = 0;
  getCollaborationParameters: GetCollaborationParameters = {};

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private collaborationService: CollaborationService,
    private permissionService: PermissionService
  ) {}

  async ngOnInit(): Promise<void> {
    this.setPermissions();
    await this.initData(1, {});
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  async handlePageEvent(e: PageEvent) {
    await this.initData(e.pageIndex + 1, this.getCollaborationParameters);
  }

  handleTableClick(id: string): void {
    this.router.navigate([routePaths.collaboration, id]);
  }

  private async initData(page: number, parameters: GetCollaborationParameters) {
    this.isLoading = true;
    this.currentPage = page;
    this.getCollaborationParameters = { ...parameters, sort: CollaborationSortProperties.Name };
    await this.getCollaborations(page, this.getCollaborationParameters);
    this.isLoading = false;
  }

  private async getCollaborations(page: number, parameters: GetCollaborationParameters) {
    const result = await this.collaborationService.getPaginatedCollaborations(page, parameters);

    this.table = {
      columns: [
        { id: 'id', label: this.translateService.instant('general.id') },
        {
          id: 'name',
          label: this.translateService.instant('collaboration.name'),
          searchEnabled: true,
          initSearchString: unlikeApiParameter(parameters.name)
        },
        { id: 'encrypted', label: this.translateService.instant('collaboration.encrypted') }
      ],
      rows: result.data.map((_) => ({
        id: _.id.toString(),
        columnData: {
          id: _.id,
          name: _.name,
          encrypted: _.encrypted ? this.translateService.instant('general.yes') : this.translateService.instant('general.no')
        }
      }))
    };
    this.pagination = result.links;
  }

  public handleSearchChanged(searchRequests: SearchRequest[]): void {
    const parameters: GetCollaborationParameters = getApiSearchParameters<GetCollaborationParameters>(searchRequests);
    this.initData(1, parameters);
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canCreate = this.permissionService.isAllowed(ScopeType.GLOBAL, ResourceType.COLLABORATION, OperationType.CREATE);
        }
      });
  }
}
