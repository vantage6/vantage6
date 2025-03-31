import { DatePipe, NgIf } from '@angular/common';
import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatCard, MatCardContent, MatCardHeader, MatCardTitle } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatMenu, MatMenuTrigger } from '@angular/material/menu';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { PageHeaderComponent } from 'src/app/components/page-header/page-header.component';
import { SearchRequest, TableComponent } from 'src/app/components/table/table.component';
import { getApiSearchParameters } from 'src/app/helpers/api.helper';
import { getChipTypeForStatus, getTaskStatusTranslation } from 'src/app/helpers/task.helper';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { Dataframe } from 'src/app/models/api/session.models';
import { BaseTask, GetTaskParameters } from 'src/app/models/api/task.models';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { SessionService } from 'src/app/services/session.service';
import { TaskService } from 'src/app/services/task.service';

@Component({
  selector: 'app-dataframe-read',
  templateUrl: './dataframe-read.component.html',
  styleUrl: './dataframe-read.component.scss',
  imports: [
    PageHeaderComponent,
    MatIcon,
    MatMenuTrigger,
    TranslateModule,
    MatMenu,
    NgIf,
    MatCard,
    MatCardContent,
    MatProgressSpinner,
    MatCardHeader,
    MatCardTitle,
    TableComponent,
    MatPaginator
  ]
})
export class DataframeReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';

  destroy$ = new Subject();
  currentPage: number = 1;

  getDataframeTasksParameters: GetTaskParameters = {};
  pagination: PaginationLinks | null = null;
  dataframeTasksTable: TableData | undefined;

  isLoading = true;
  dataframe: Dataframe | null = null;
  canDelete = false;
  canEdit = false;

  constructor(
    private translateService: TranslateService,
    private activatedRoute: ActivatedRoute,
    private sessionService: SessionService,
    private chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService,
    private taskService: TaskService,
    private datePipe: DatePipe,
    private router: Router
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
  }

  async initData(): Promise<void> {
    if (!this.id) return;
    this.dataframe = await this.sessionService.getDataframe(Number(this.id));
    if (this.dataframe) {
      await this.getDataframeTasks();
    }
    this.isLoading = false;
  }

  private async getDataframeTasks(): Promise<void> {
    this.isLoading = true;
    const dataframeTasks = await this.taskService.getPaginatedTasks(this.currentPage, {
      dataframe_id: this.dataframe?.id
    });
    this.pagination = dataframeTasks.links;

    this.dataframeTasksTable = {
      columns: [
        { id: 'id', label: this.translateService.instant('general.id') },
        { id: 'name', label: this.translateService.instant('general.name'), searchEnabled: true },
        {
          id: 'status',
          label: this.translateService.instant('task.status'),
          filterEnabled: true,
          isChip: true,
          chipTypeProperty: 'statusType'
        }
      ],
      rows: dataframeTasks.data.map((task) => {
        return {
          id: task.id.toString(),
          columnData: {
            id: task.id,
            name: task.name,
            status: getTaskStatusTranslation(this.translateService, task.status),
            statusType: getChipTypeForStatus(task.status),
            created_date: this.datePipe.transform(task.created_at, 'yyyy-MM-dd HH:mm')
          }
        };
      })
    };
  }

  handleTaskTableClick(task_id: string) {
    this.router.navigate([routePaths.task, task_id]);
  }

  handleSearchChanged(searchRequests: SearchRequest[]): void {
    this.getDataframeTasksParameters = getApiSearchParameters<GetTaskParameters>(searchRequests);
    this.currentPage = 1;
    this.getDataframeTasks();
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getDataframeTasks();
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
        }
      });
  }
}
