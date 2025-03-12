import { NgIf } from '@angular/common';
import { Component, HostBinding, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { MatButton } from '@angular/material/button';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { Router, RouterLink } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subject, combineLatest, takeUntil } from 'rxjs';
import { PageHeaderComponent } from 'src/app/components/page-header/page-header.component';
import { SearchRequest, TableComponent } from 'src/app/components/table/table.component';
import { getApiSearchParameters } from 'src/app/helpers/api.helper';
import { unlikeApiParameter } from 'src/app/helpers/general.helper';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { BaseSession, GetSessionParameters, SessionSortProperties } from 'src/app/models/api/session.models';
import { TableData } from 'src/app/models/application/table.model';
import { CHOSEN_COLLABORATION, USER_ID } from 'src/app/models/constants/sessionStorage';
import { routePaths } from 'src/app/routes';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { SessionService } from 'src/app/services/session.service';

enum TableRows {
  ID = 'id',
  Name = 'name'
}

@Component({
  selector: 'app-session-list',
  templateUrl: './session-list.component.html',
  imports: [
    PageHeaderComponent,
    TableComponent,
    MatCard,
    MatCardContent,
    MatIcon,
    TranslateModule,
    MatPaginator,
    RouterLink,
    NgIf,
    MatButton
  ]
})
export class SessionListComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @ViewChild(MatPaginator) paginator?: MatPaginator;
  tableRows = TableRows;
  routes = routePaths;
  destroy$ = new Subject();

  sessions: BaseSession[] = [];
  table?: TableData;
  displayedColumns: string[] = [TableRows.ID, TableRows.Name];
  isLoading: boolean = true;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;
  currentSearchInput: string = '';
  canCreate: boolean = false;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private sessionService: SessionService,
    private chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService
  ) {}

  async ngOnInit() {
    this.setPermissions();
    await this.initData(this.currentPage, { sort: SessionSortProperties.ID });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    const parameters: GetSessionParameters = { sort: SessionSortProperties.ID };
    if (this.currentSearchInput?.length) {
      parameters.name = this.currentSearchInput;
    }
    await this.getSessions(this.currentPage, parameters);
  }

  handleSearchChanged(searchRequests: SearchRequest[]) {
    this.isLoading = true;
    const parameters: GetSessionParameters = getApiSearchParameters<GetSessionParameters>(searchRequests);
    this.currentSearchInput = parameters?.name ?? '';
    this.paginator?.firstPage();
    this.initData(1, parameters);
  }

  handleRowKeyPress(event: KeyboardEvent, session: BaseSession) {
    if (event.key === 'Enter' || event.key === ' ') {
      this.handleTableClick(session.id.toString());
    }
  }

  handleTableClick(session_id: string) {
    this.router.navigate([routePaths.session, session_id]);
  }

  private async initData(page: number, parameters: GetSessionParameters) {
    await this.getSessions(page, parameters);
    this.isLoading = false;
  }

  private async getSessions(page: number, parameters: GetSessionParameters) {
    const collaborationID = sessionStorage.getItem(CHOSEN_COLLABORATION);
    const userID = sessionStorage.getItem(USER_ID);
    if (!collaborationID || !userID) return;

    parameters = { ...parameters, collaboration_id: collaborationID };
    const sessionData = await this.sessionService.getPaginatedSessions(page, parameters);
    this.sessions = sessionData.data;
    this.pagination = sessionData.links;

    this.table = {
      columns: [
        {
          id: TableRows.ID,
          label: this.translateService.instant('general.id')
        },
        {
          id: TableRows.Name,
          label: this.translateService.instant('general.name'),
          searchEnabled: true,
          initSearchString: unlikeApiParameter(parameters.name)
        }
      ],
      rows: this.sessions.map((_) => ({
        id: _.id.toString(),
        columnData: {
          id: _.id.toString(),
          name: _.name
        }
      }))
    };
  }

  private setPermissions() {
    const permissionInit = this.permissionService.isInitialized();
    const chosenCollab = this.chosenCollaborationService.collaboration$.asObservable();
    combineLatest([permissionInit, chosenCollab])
      .pipe(takeUntil(this.destroy$))
      .subscribe(([initialized, collab]) => {
        if (initialized && collab !== null) {
          this.canCreate = this.permissionService.isAllowedForCollab(
            ResourceType.SESSION,
            OperationType.CREATE,
            this.chosenCollaborationService.collaboration$.value
          );
        }
      });
  }
}
