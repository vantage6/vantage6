import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { routePaths } from 'src/app/routes';
import { MatDialog } from '@angular/material/dialog';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { ActivatedRoute, Router } from '@angular/router';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { printDate } from 'src/app/helpers/general.helper';
import { StudyService } from 'src/app/services/study.service';
import { Study } from 'src/app/models/api/study.model';
import { GetDataframeParameters, Session, SessionLazyProperties, SessionScope } from 'src/app/models/api/session.models';
import { SessionService } from 'src/app/services/session.service';
import { User, UserLazyProperties } from 'src/app/models/api/user.model';
import { UserService } from 'src/app/services/user.service';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { PageHeaderComponent } from 'src/app/components/page-header/page-header.component';
import { MatMenu, MatMenuItem, MatMenuTrigger } from '@angular/material/menu';
import { MatIcon } from '@angular/material/icon';
import { MatCard, MatCardContent, MatCardHeader, MatCardTitle } from '@angular/material/card';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { NgIf } from '@angular/common';
import { MatButton, MatIconButton } from '@angular/material/button';
import { TableData } from 'src/app/models/application/table.model';
import { SearchRequest, TableComponent } from 'src/app/components/table/table.component';
import { getApiSearchParameters } from 'src/app/helpers/api.helper';
import { PaginationLinks } from 'src/app/models/api/pagination.model';

@Component({
  selector: 'app-session-read',
  templateUrl: './session-read.component.html',
  styleUrls: ['./session-read.component.scss'],
  imports: [
    PageHeaderComponent,
    MatMenuTrigger,
    MatIcon,
    MatMenu,
    TranslateModule,
    MatCard,
    MatCardHeader,
    MatCardContent,
    MatCardTitle,
    MatProgressSpinner,
    NgIf,
    PageHeaderComponent,
    MatIconButton,
    MatMenuItem,
    MatButton,
    TableComponent,
    MatPaginator
  ]
})
export class SessionReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';
  printDate = printDate;
  sessionScope = SessionScope;

  destroy$ = new Subject();
  waitTaskComplete$ = new Subject();
  routes = routePaths;
  currentPage: number = 1;

  session: Session | null = null;
  dataframeTable: TableData | undefined;
  pagination: PaginationLinks | null = null;

  getDataframeParameters: GetDataframeParameters = {};
  study: Study | null = null;
  owner: User | null = null;
  isLoading = true;
  canDelete = false;
  canEdit = false;
  canCreate = false;

  private nodeStatusUpdateSubscription?: Subscription;
  private taskStatusUpdateSubscription?: Subscription;
  private taskNewUpdateSubscription?: Subscription;

  constructor(
    public dialog: MatDialog,
    private router: Router,
    private activatedRoute: ActivatedRoute,
    private translateService: TranslateService,
    private sessionService: SessionService,
    private studyService: StudyService,
    private userService: UserService,
    private chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService
  ) {}

  async ngOnInit(): Promise<void> {
    this.setPermissions();

    // subscribe to reload task data when url changes (i.e. other task is viewed)
    this.activatedRoute.params.pipe(takeUntil(this.destroy$)).subscribe(async (params) => {
      this.id = params['id'];
      this.isLoading = true;
      await this.initData();
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
    this.waitTaskComplete$.next(true);
    this.taskStatusUpdateSubscription?.unsubscribe();
    this.taskNewUpdateSubscription?.unsubscribe();
    this.nodeStatusUpdateSubscription?.unsubscribe();
  }

  async initData(): Promise<void> {
    if (!this.session) {
      this.session = await this.getSession();
      if (this.session.study) this.study = await this.studyService.getStudy(this.session.study.id.toString());
      if (this.session.owner)
        this.owner = await this.userService.getUser(this.session.owner.id.toString(), [UserLazyProperties.Organization]);
      await this.getDataframes();
    }
    this.isLoading = false;
  }

  async getDataframes(): Promise<void> {
    const dataframeResponse = await this.sessionService.getPaginatedDataframes(
      Number.parseInt(this.id),
      this.currentPage,
      this.getDataframeParameters
    );
    this.pagination = dataframeResponse.links;
    this.dataframeTable = {
      columns: [
        { id: 'id', label: this.translateService.instant('general.id') },
        { id: 'name', label: this.translateService.instant('general.name'), searchEnabled: true },
        { id: 'db', label: this.translateService.instant('session.dataframes.db-label-short'), searchEnabled: true },
        { id: 'ready', label: this.translateService.instant('session.dataframes.ready') }
      ],
      rows: dataframeResponse.data.map((_) => ({
        id: _.id.toString(),
        columnData: {
          id: _.id,
          name: _.name,
          db: _.db_label,
          ready: _.ready ? this.translateService.instant('general.yes') : this.translateService.instant('general.no')
        }
      }))
    };
  }

  handleDataframeTableClick(id: string): void {
    this.router.navigate([routePaths.sessionDataframe.replace(':sessionId', this.id), id]);
  }

  hasDataframes(): boolean {
    return this.dataframeTable !== undefined && this.dataframeTable.rows.length > 0;
  }

  translateScope(scope: SessionScope): string {
    switch (scope) {
      case SessionScope.Collaboration:
        return this.translateService.instant('rule.scope.collaboration');
      case SessionScope.Organization:
        return this.translateService.instant('rule.scope.organization');
      case SessionScope.Own:
        return this.translateService.instant('rule.scope.own');
      default:
        return scope;
    }
  }

  public handleSearchChanged(searchRequests: SearchRequest[]): void {
    this.getDataframeParameters = getApiSearchParameters<GetDataframeParameters>(searchRequests);
    this.currentPage = 1;
    this.getDataframes();
  }

  async addDataframe() {
    this.router.navigate([routePaths.dataframeCreate, this.id]);
  }

  async deleteDataframe(dfID: number) {
    this.sessionService.deleteDataframe(dfID);
    this.getDataframes();
  }

  async getSession(): Promise<Session> {
    return await this.sessionService.getSession(Number.parseInt(this.id), [SessionLazyProperties.Owner]);
  }

  async handleDelete(): Promise<void> {
    if (!this.session) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('session.delete-title', { name: this.session.name }),
        content: this.translateService.instant('session.delete-content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === true) {
          if (!this.session) return;
          this.isLoading = true;
          await this.sessionService.deleteSession(this.session.id);
          this.router.navigate([routePaths.sessions]);
        }
      });
  }

  handleEdit() {
    this.router.navigate([routePaths.sessionEdit, this.id]);
  }

  newAnalysis() {
    const newPath = routePaths.sessionTaskCreate.replace(':sessionId', this.id);
    this.router.navigate([newPath]);
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getDataframes();
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canDelete = this.permissionService.isAllowedForCollab(
            ResourceType.SESSION,
            OperationType.DELETE,
            this.chosenCollaborationService.collaboration$.value
          );
          this.canEdit = this.permissionService.isAllowedForCollab(
            ResourceType.SESSION,
            OperationType.EDIT,
            this.chosenCollaborationService.collaboration$.value
          );
          this.canCreate = this.permissionService.isAllowedForCollab(
            ResourceType.TASK,
            OperationType.CREATE,
            this.chosenCollaborationService.collaboration$.value
          );
        }
      });
  }
}
