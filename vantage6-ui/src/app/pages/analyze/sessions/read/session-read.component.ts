import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { routePaths } from 'src/app/routes';
import { MatDialog } from '@angular/material/dialog';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { ActivatedRoute, Router } from '@angular/router';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { Subject, Subscription, takeUntil, timer } from 'rxjs';
import { printDate } from 'src/app/helpers/general.helper';
import { StudyService } from 'src/app/services/study.service';
import { Study } from 'src/app/models/api/study.model';
import { Dataframe, Session, SessionLazyProperties } from 'src/app/models/api/session.models';
import { SessionService } from 'src/app/services/session.service';
import { User } from 'src/app/models/api/user.model';
import { UserService } from 'src/app/services/user.service';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { PageEvent } from '@angular/material/paginator';

@Component({
  selector: 'app-session-read',
  templateUrl: './session-read.component.html',
  styleUrls: ['./session-read.component.scss']
})
export class SessionReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';
  printDate = printDate;

  destroy$ = new Subject();
  waitTaskComplete$ = new Subject();
  routes = routePaths;
  currentPage: number = 1;

  session: Session | null = null;
  dataframes: Dataframe[] = [];
  dataframePaginagion: PaginationLinks | null = null;
  selectedDataframe?: Dataframe;
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
      if (this.session.owner) this.owner = await this.userService.getUser(this.session.owner.id.toString());
      this.getDataframes();
    }
    this.isLoading = false;
  }

  async getDataframes() {
    const dataframeResponse = await this.sessionService.getPaginatedDataframes(Number.parseInt(this.id), this.currentPage);
    this.dataframes = dataframeResponse.data;
    this.dataframePaginagion = this.dataframePaginagion;
  }

  async handleDataframeChange(handle: string): Promise<void> {
    // TODO(BART/RIAN) RIAN: When the backend response is customized the additional information about the dataframe needs to be processed here and in the template.
    this.selectedDataframe = undefined;
    this.selectedDataframe = await this.sessionService.getDataframe(Number.parseInt(this.id), handle);
  }

  async addDataframe() {
    this.router.navigate([routePaths.dataframeCreate, this.id]);
  }

  async deleteDataframe(dataframe_handle: string) {
    this.sessionService.deleteDataframe(Number.parseInt(this.id), dataframe_handle);
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
