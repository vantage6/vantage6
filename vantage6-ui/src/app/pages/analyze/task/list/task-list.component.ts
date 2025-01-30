import { DatePipe } from '@angular/common';
import { Component, HostBinding, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, Subscription, combineLatest, takeUntil } from 'rxjs';
import { SearchRequest } from 'src/app/components/table/table.component';
import { getApiSearchParameters } from 'src/app/helpers/api.helper';
import { unlikeApiParameter } from 'src/app/helpers/general.helper';
import { getChipTypeForStatus, getTaskStatusTranslation } from 'src/app/helpers/task.helper';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { BaseTask, GetTaskParameters, TaskSortProperties, TaskStatus } from 'src/app/models/api/task.models';
import { TableData } from 'src/app/models/application/table.model';
import { CHOSEN_COLLABORATION, USER_ID } from 'src/app/models/constants/sessionStorage';
import { AlgorithmStatusChangeMsg } from 'src/app/models/socket-messages.model';
import { routePaths } from 'src/app/routes';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { TaskService } from 'src/app/services/task.service';

enum TableRows {
  ID = 'id',
  Name = 'name',
  Status = 'status',
  CreatedDate = 'created_date'
}

@Component({
  selector: 'app-task-list',
  templateUrl: './task-list.component.html'
})
export class TaskListComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @ViewChild(MatPaginator) paginator?: MatPaginator;
  tableRows = TableRows;
  routes = routePaths;
  destroy$ = new Subject();

  tasks: BaseTask[] = [];
  table?: TableData;
  displayedColumns: string[] = [TableRows.ID, TableRows.Name, TableRows.Status];
  isLoading: boolean = true;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;
  currentSearchInput: string = '';
  canCreate: boolean = false;

  private taskStatusUpdateSubscription?: Subscription;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private taskService: TaskService,
    private chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService,
    private socketioConnectService: SocketioConnectService,
    private datePipe: DatePipe
  ) {}

  async ngOnInit() {
    this.setPermissions();

    await this.initData(this.currentPage, { sort: TaskSortProperties.ID, is_user_created: 1 });
    this.taskStatusUpdateSubscription = this.socketioConnectService
      .getAlgorithmStatusUpdates()
      .subscribe((statusUpdate: AlgorithmStatusChangeMsg | null) => {
        if (statusUpdate) this.onAlgorithmStatusUpdate(statusUpdate);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
    this.taskStatusUpdateSubscription?.unsubscribe();
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    const parameters: GetTaskParameters = { sort: TaskSortProperties.ID, is_user_created: 1 };
    if (this.currentSearchInput?.length) {
      delete parameters.is_user_created;
      parameters.name = this.currentSearchInput;
    }
    await this.getTasks(this.currentPage, parameters);
  }

  handleSearchChanged(searchRequests: SearchRequest[]) {
    this.isLoading = true;
    const parameters: GetTaskParameters = getApiSearchParameters<GetTaskParameters>(searchRequests);
    this.currentSearchInput = parameters?.name ?? '';
    if (!parameters?.name?.length) parameters.is_user_created = 1;
    this.paginator?.firstPage();
    this.initData(1, parameters);
  }

  handleTableClick(task_id: string) {
    this.router.navigate([routePaths.task, task_id]);
  }

  handleRowKeyPress(event: KeyboardEvent, task: BaseTask) {
    if (event.key === 'Enter' || event.key === ' ') {
      this.handleTableClick(task.id.toString());
    }
  }

  getChipTypeForStatus(status: TaskStatus) {
    return getChipTypeForStatus(status);
  }

  getTaskStatusTranslation(status: TaskStatus) {
    return getTaskStatusTranslation(this.translateService, status);
  }

  private async initData(page: number, parameters: GetTaskParameters) {
    await this.getTasks(page, parameters);
    this.isLoading = false;
  }

  private async getTasks(page: number, parameters: GetTaskParameters) {
    const collaborationID = sessionStorage.getItem(CHOSEN_COLLABORATION);
    const userID = sessionStorage.getItem(USER_ID);
    if (!collaborationID || !userID) return;

    parameters = { ...parameters, collaboration_id: collaborationID };
    const taskData = await this.taskService.getPaginatedTasks(page, parameters);
    this.tasks = taskData.data;
    this.pagination = taskData.links;

    this.table = {
      columns: [
        {
          id: TableRows.ID,
          label: this.translateService.instant('general.id')
        },
        {
          id: TableRows.Name,
          label: this.translateService.instant('task.name'),
          searchEnabled: true,
          initSearchString: unlikeApiParameter(parameters.name)
        },
        {
          id: TableRows.Status,
          label: this.translateService.instant('task.status'),
          filterEnabled: true,
          isChip: true,
          chipTypeProperty: 'statusType'
        },
        {
          id: TableRows.CreatedDate,
          label: this.translateService.instant('task.created-at'),
          filterEnabled: false
        }
      ],
      rows: this.tasks.map((_) => ({
        id: _.id.toString(),
        columnData: {
          id: _.id.toString(),
          name: _.name,
          status: this.getTaskStatusTranslation(_.status),
          statusType: this.getChipTypeForStatus(_.status),
          created_date: this.datePipe.transform(_.created_at, 'yyyy-MM-dd HH:mm')
        }
      }))
    };
  }

  private async onAlgorithmStatusUpdate(statusUpdate: AlgorithmStatusChangeMsg) {
    const task = this.tasks.find((t) => t.id === statusUpdate.task_id);
    if (task) {
      task.status = statusUpdate.status as TaskStatus;
    }
  }

  private setPermissions() {
    // to determine whether we can create task, both the permission service AND the chosen
    // collaboration have to be initialized
    const permissionInit = this.permissionService.isInitialized();
    const chosenCollab = this.chosenCollaborationService.collaboration$.asObservable();
    combineLatest([permissionInit, chosenCollab])
      .pipe(takeUntil(this.destroy$))
      .subscribe(([initialized, collab]) => {
        if (initialized && collab !== null) {
          this.canCreate = this.permissionService.isAllowedForCollab(
            ResourceType.TASK,
            OperationType.CREATE,
            this.chosenCollaborationService.collaboration$.value
          );
        }
      });
  }
}
