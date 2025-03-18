import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { getChipTypeForStatus, getStatusType, getTaskStatusTranslation } from 'src/app/helpers/task.helper';
import { Algorithm, AlgorithmFunction, Argument, ArgumentType } from 'src/app/models/api/algorithm.model';
import { Visualization } from 'src/app/models/api/visualization.model';
import {
  Task,
  TaskLazyProperties,
  TaskRun,
  TaskStatus,
  TaskResult,
  BaseTask,
  TaskStatusGroup,
  TaskParameter
} from 'src/app/models/api/task.models';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { TaskService } from 'src/app/services/task.service';
import { LogDialogComponent } from 'src/app/components/dialogs/log/log-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { Subject, Subscription, takeUntil, timer } from 'rxjs';
import { FileService } from 'src/app/services/file.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { AlgorithmLogMsg, AlgorithmStatusChangeMsg, NewTaskMsg, NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import {
  THRESHOLD_LONG_PARAMETER_TEXT,
  THRESHOLD_LONG_TEXT,
  THRESHOLD_PRINTABLE_TEXT,
  THRESHOLD_SMALL_TILES
} from 'src/app/models/constants/thresholds';
import { WAIT_200_MILLISECONDS } from 'src/app/models/constants/wait';
import { NodeStatus } from 'src/app/models/api/node.model';
import { printDate } from 'src/app/helpers/general.helper';
import { AlgorithmStoreService } from 'src/app/services/algorithm-store.service';
import { StudyService } from 'src/app/services/study.service';
import { Study } from 'src/app/models/api/study.model';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf, NgClass, NgFor, SlicePipe } from '@angular/common';
import { MatIconButton, MatButton } from '@angular/material/button';
import { MatMenuTrigger, MatMenu, MatMenuItem } from '@angular/material/menu';
import { MatIcon } from '@angular/material/icon';
import { AlertComponent } from '../../../../components/alerts/alert/alert.component';
import { MatCard, MatCardActions, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import {
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
  MatAccordion,
  MatExpansionPanelDescription
} from '@angular/material/expansion';
import { StatusInfoComponent } from '../../../../components/helpers/status-info/status-info.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatSelect } from '@angular/material/select';
import { MatOption } from '@angular/material/core';
import { VisualizeResultComponent } from '../../../../components/visualization/visualize-result/visualize-result.component';
import { ChipComponent } from '../../../../components/helpers/chip/chip.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { OrderByPipe } from '../../../../pipes/order-by.pipe';
import { OrderByTaskStatusPipe } from '../../../../pipes/order-by-status.pipe';
import { AlgorithmStepType, Session } from 'src/app/models/api/session.models';
import { SessionService } from 'src/app/services/session.service';

@Component({
  selector: 'app-task-read',
  templateUrl: './task-read.component.html',
  styleUrls: ['./task-read.component.scss'],
  imports: [
    PageHeaderComponent,
    NgIf,
    MatIconButton,
    MatMenuTrigger,
    MatIcon,
    MatMenu,
    MatMenuItem,
    AlertComponent,
    MatCard,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    NgClass,
    NgFor,
    StatusInfoComponent,
    MatButton,
    MatCardActions,
    MatCardHeader,
    MatCardTitle,
    MatFormField,
    MatLabel,
    MatSelect,
    ReactiveFormsModule,
    MatOption,
    MatCardContent,
    VisualizeResultComponent,
    ChipComponent,
    RouterLink,
    MatAccordion,
    MatExpansionPanelDescription,
    MatProgressSpinner,
    SlicePipe,
    TranslateModule,
    OrderByPipe,
    OrderByTaskStatusPipe
  ]
})
export class TaskReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';
  algorithmStepType = AlgorithmStepType;
  printDate = printDate;

  destroy$ = new Subject();
  waitTaskComplete$ = new Subject();
  routes = routePaths;

  visualization = new FormControl(0);

  task: Task | null = null;
  session: Session | null = null;
  childTasks: BaseTask[] = [];
  study: Study | null = null;
  algorithm: Algorithm | null = null;
  function: AlgorithmFunction | null = null;
  selectedVisualization: Visualization | null = null;
  isLoading = true;
  canDelete = false;
  canCreate = false;
  canKill = false;
  algorithmNotFoundInStore = false;
  showAllChildTasks = false;
  logs: { [runId: number]: string[] } = {};

  private nodeStatusUpdateSubscription?: Subscription;
  private taskStatusUpdateSubscription?: Subscription;
  private taskNewUpdateSubscription?: Subscription;

  constructor(
    public dialog: MatDialog,
    private router: Router,
    private activatedRoute: ActivatedRoute,
    private translateService: TranslateService,
    private taskService: TaskService,
    private sessionService: SessionService,
    private studyService: StudyService,
    private algorithmService: AlgorithmService,
    private algorithmStoreService: AlgorithmStoreService,
    private chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService,
    private fileService: FileService,
    private socketioConnectService: SocketioConnectService
  ) {}

  async ngOnInit(): Promise<void> {
    this.setPermissions();
    this.visualization.valueChanges.subscribe((value) => {
      this.selectedVisualization = this.function?.ui_visualizations?.[value || 0] || null;
    });

    // subscribe to reload task data when url changes (i.e. other task is viewed)
    this.activatedRoute.params.pipe(takeUntil(this.destroy$)).subscribe(async (params) => {
      this.id = params['id'];
      this.isLoading = true;
      await this.initData();
    });

    // subscribe to task updates
    this.taskStatusUpdateSubscription = this.socketioConnectService
      .getAlgorithmStatusUpdates()
      .subscribe((statusUpdate: AlgorithmStatusChangeMsg | null) => {
        if (statusUpdate) this.onAlgorithmStatusUpdate(statusUpdate);
      });

    // subscribe to new tasks
    this.taskNewUpdateSubscription = this.socketioConnectService.getNewTaskUpdates().subscribe((newTaskMsg: NewTaskMsg | null) => {
      if (newTaskMsg) this.onNewTask(newTaskMsg);
    });
    // subscribe to node status updates
    this.nodeStatusUpdateSubscription = this.socketioConnectService
      .getNodeStatusUpdates()
      .subscribe((nodeStatus: NodeOnlineStatusMsg | null) => {
        if (nodeStatus) this.onNodeStatusUpdate(nodeStatus);
      });

    this.socketioConnectService.getAlgorithmLogUpdates().subscribe((logMsg: AlgorithmLogMsg | null) => {
      if (logMsg) this.onLogUpdate(logMsg);
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
    this.waitTaskComplete$.next(true);
    this.taskStatusUpdateSubscription?.unsubscribe();
    this.taskNewUpdateSubscription?.unsubscribe();
    this.nodeStatusUpdateSubscription?.unsubscribe();
  }

  async initData(sync_tasks: boolean = true): Promise<void> {
    if (!this.task || sync_tasks) {
      this.task = await this.getMainTask();
      this.childTasks = await this.getChildTasks();
      if (this.task.session) this.session = await this.sessionService.getSession(this.task.session.id);
      if (this.task.study) this.study = await this.studyService.getStudy(this.task.study.id.toString());
    }
    try {
      if (this.task.algorithm_store) {
        const store = await this.algorithmStoreService.getAlgorithmStore(this.task.algorithm_store?.id.toString());
        this.algorithm = await this.algorithmService.getAlgorithmByUrl(this.task.image, store);
        // Please note, the function cannot be set if the input cannot be decoded. This will result in NO visualization and information about the function.
        this.function = this.algorithm?.functions.find((_) => _.name === this.task?.method) || null;
        if (!this.selectedVisualization) {
          // by checking in if statement whether visualization was already set, we prevent
          // the visualization from being reset to the first one when the task is reloaded
          this.selectedVisualization = this.function?.ui_visualizations?.[0] || null;
        }
      } else {
        this.algorithmNotFoundInStore = true;
      }
    } catch (error) {
      // error message is already displayed - we only catch failure to get the algorithm
      // here.
      this.algorithmNotFoundInStore = true;
    }
    this.isLoading = false;
  }

  private onLogUpdate(logMsg: AlgorithmLogMsg): void {
    // update logs of main and child task runs
    [this.task, ...this.childTasks].forEach((task: Task | BaseTask | null) => {
      if (!task) return;
      const run = task.runs.find((run) => run.id === logMsg.run_id);
      this.appendLog(run, logMsg);
    });
  }

  private appendLog(run: TaskRun | undefined, logMsg: AlgorithmLogMsg) {
    if (run) {
      if (!run.log) {
        run.log = '';
      } else if (!run.log.endsWith('\n')) {
        run.log += '\n';
      }
      run.log += `${logMsg.log}`;
    }
  }

  async getMainTask(): Promise<Task> {
    return await this.taskService.getTask(Number.parseInt(this.id), [TaskLazyProperties.InitOrg, TaskLazyProperties.InitUser]);
  }

  getChipTypeForStatus(status: TaskStatus) {
    return getChipTypeForStatus(status);
  }

  getTaskStatusTranslation(status: TaskStatus) {
    return getTaskStatusTranslation(this.translateService, status);
  }

  getStatusType(status: TaskStatus) {
    return getStatusType(status);
  }

  async getChildTasks(): Promise<BaseTask[]> {
    return await this.taskService.getTasks({ parent_id: this.task?.id, include: 'results,runs' });
  }

  isTaskComplete(): boolean {
    if (!this.task) return true;
    if (this.task.runs.length <= 0) return true;
    if (this.task.results?.some((result) => result.result === null)) return false;
    if (this.task.runs.every((run) => run.status === TaskStatus.Completed)) return true;
    return false;
  }

  isSmallTileView(): boolean {
    const runs = this.childTasks.flatMap((tasks) => tasks.runs) ?? [];
    return runs.length > THRESHOLD_SMALL_TILES;
  }

  isFailedRun(status: TaskStatus): boolean {
    return (
      status === TaskStatus.Failed ||
      status === TaskStatus.Crashed ||
      status === TaskStatus.NoDockerImage ||
      status === TaskStatus.StartFailed ||
      status === TaskStatus.Killed
    );
  }

  isActive(status: TaskStatus): boolean {
    return status === TaskStatus.Pending || status === TaskStatus.Initializing || status === TaskStatus.Active;
  }

  openLog(run: TaskRun): void {
    const dialogRef = this.dialog.open(LogDialogComponent, {
      width: '80vw',
      data: {
        log: run.log || 'No logs available'
      }
    });

    const logSubscription = this.socketioConnectService.getAlgorithmLogUpdates().subscribe((logMsg: AlgorithmLogMsg | null) => {
      if (logMsg && logMsg.run_id === run.id) {
        if (!run.log) {
          run.log = '';
        }
        dialogRef.componentInstance.data.log = run.log;
      }
    });

    dialogRef.afterClosed().subscribe(() => {
      logSubscription.unsubscribe();
    });
  }

  getRunForResult(id: number): TaskRun | undefined {
    return this.task?.runs.find((_) => _.id === id);
  }

  async handleDelete(): Promise<void> {
    if (!this.task) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('task-read.delete-dialog.title', { name: this.task.name }),
        content: this.translateService.instant('task-read.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === true) {
          if (!this.task) return;
          this.isLoading = true;
          await this.taskService.deleteTask(this.task.id);
          this.router.navigate([routePaths.tasks]);
        }
      });
  }

  handleRepeat(): void {
    if (!this.task) return;
    this.router.navigate([routePaths.taskCreateRepeat, this.task.id]);
  }

  handleTaskKill(): void {
    if (!this.task) return;

    // ask for confirmation
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('task-read.kill-dialog.title', { name: this.task.name }),
        content: this.translateService.instant('task-read.kill-dialog.content'),
        confirmButtonText: this.translateService.instant('task-read.card-status.actions.kill'),
        confirmButtonType: 'warn'
      }
    });

    // execute kill (if confirmed)
    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === true) {
          if (!this.task) return;
          await this.taskService.killTask(this.task.id);
          this.task.status == TaskStatus.Killed;
          // renew task data to get the updated status
          this.initData(true);
        }
      });
  }

  displayTextResult(result: object | undefined): string {
    if (result === undefined) return '';
    const textResult = JSON.stringify(result);
    if (textResult.length > THRESHOLD_LONG_TEXT) {
      return textResult.substring(0, THRESHOLD_LONG_TEXT) + '...';
    }
    return textResult;
  }

  getParameterDisplayName(parameter: TaskParameter): string {
    const argument: Argument | undefined = this.function?.arguments.find((_) => _.name === parameter.label);
    if (argument) {
      return argument.display_name ?? argument.name;
    } else {
      return parameter.label;
    }
  }

  getParameterValueAsString(parameter: TaskParameter): string {
    const argument: Argument | undefined = this.function?.arguments.find((_) => _.name === parameter.label);
    let parameter_str = argument?.type !== ArgumentType.Json ? parameter.value : JSON.stringify(parameter.value);
    if (parameter_str.length > THRESHOLD_LONG_PARAMETER_TEXT) {
      const len_not_displayed = parameter_str.length - THRESHOLD_LONG_PARAMETER_TEXT;
      parameter_str = parameter_str.substring(0, THRESHOLD_LONG_PARAMETER_TEXT) + '... (' + len_not_displayed + ' more characters)';
    }

    return parameter_str;
  }

  downloadInput(run: TaskRun): void {
    const filename = `vantage6_input_${run.id}.txt`;
    const textInput = run.input || '';
    this.fileService.downloadTxtFile(textInput, filename);
  }

  downloadResult(result: TaskResult): void {
    const filename = `vantage6_result_${result.id}.txt`;
    let textResult = '';
    if (result.decoded_result === undefined) {
      textResult = result.result || '';
    } else {
      textResult = JSON.stringify(result.decoded_result);
    }
    this.fileService.downloadTxtFile(textResult, filename);
  }

  getPrintableTaskName(task: Task): string {
    if (task.name.length > THRESHOLD_PRINTABLE_TEXT) {
      return task.name.substring(0, THRESHOLD_PRINTABLE_TEXT) + '...';
    } else {
      return task.name;
    }
  }

  private async waitUntilInitialized(): Promise<void> {
    while (this.isLoading) {
      await new Promise((f) => setTimeout(f, WAIT_200_MILLISECONDS));
    }
  }

  private async onAlgorithmStatusUpdate(statusUpdate: AlgorithmStatusChangeMsg): Promise<void> {
    await this.waitUntilInitialized();
    // Update status of child tasks
    this.childTasks.forEach((task: BaseTask) => {
      if (task.id === statusUpdate.task_id) {
        task.runs.forEach((run: TaskRun) => {
          if (run.id === statusUpdate.run_id) {
            run.status = statusUpdate.status as TaskStatus;
          }
        });
      }
    });

    if (!this.task) return;
    if (statusUpdate.task_id !== this.task.id) return;
    // Don't update status if task has been killed - subtasks may still complete
    // in the meantime (racing condition) but we don't want to overwrite the killed status
    if (this.task.status === TaskStatus.Killed) return;

    // update the status of the runs
    const run = this.task.runs.find((r) => r.id === statusUpdate.run_id);
    if (run) {
      run.status = statusUpdate.status as TaskStatus;
    }

    // if all task runs are completed, update the status of the task itself
    if (this.task.runs.every((r) => r.status === TaskStatus.Completed)) {
      this.task.status = TaskStatus.Completed;
    } else if (this.task.runs.some((r) => getStatusType(r.status) === TaskStatusGroup.Error)) {
      this.task.status = TaskStatus.Failed;
    }

    // if the task is completed, we need to reload the task to get the results.
    // Also, if the task crashes, we should reload the task to get the logs.
    if ([TaskStatusGroup.Error, TaskStatusGroup.Success].includes(getStatusType(statusUpdate.status as TaskStatus))) {
      // Task is no longer running but we need to wait for the results to be available
      // on the server. Poll every second until the results are available.
      timer(0, 1000)
        .pipe(takeUntil(this.waitTaskComplete$))
        .subscribe({
          next: async () => {
            if (!this.task) return;
            const renewed_task = await this.getMainTask();
            // keep statuses of the task and the runs - these are updated by the socket
            // and are likely more up-to-date than the statuses at the central server
            renewed_task.status = this.task.status;
            renewed_task.runs.map((run) => {
              const old_run = this.task?.runs.find((r) => r.id === run.id);
              if (old_run) {
                run.status = old_run.status;
              }
            });
            this.task = renewed_task;
            // stop polling if task is either completed, or if it has crashed and the
            // logs are available (the latter may not be available immediately after the
            // task has crashed so then we wait another second)
            if (this.isTaskComplete() || this.taskHasErrorAndLogs()) {
              this.childTasks = await this.getChildTasks();
              this.initData(false);
              // stop polling
              this.waitTaskComplete$.next(true);
            }
          }
        });
    }
  }

  private taskHasErrorAndLogs(): boolean {
    if (!this.task) return true;
    return getStatusType(this.task.status) === TaskStatusGroup.Error && this.task.runs.every((run) => run.log != null);
  }

  private async onNewTask(newTaskMsg: NewTaskMsg): Promise<void> {
    await this.waitUntilInitialized();
    if (!this.task) return;
    if (newTaskMsg.parent_id !== this.task.id) return;

    // set the child task data
    this.childTasks = await this.getChildTasks();
  }

  private async onNodeStatusUpdate(nodeStatus: NodeOnlineStatusMsg): Promise<void> {
    await this.waitUntilInitialized();
    // first update the child tasks
    this.childTasks.forEach((task: BaseTask) => {
      task.runs.forEach((run: TaskRun) => {
        if (run.node.id === nodeStatus.id) {
          run.node.status = nodeStatus.online ? NodeStatus.Online : NodeStatus.Offline;
        }
      });
    });

    if (!this.task) return;

    // update the status of the runs
    const run = this.task.runs.find((r) => r.node.id === nodeStatus.id);
    if (run) {
      run.node.status = nodeStatus.online ? NodeStatus.Online : NodeStatus.Offline;
    }
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canDelete = this.permissionService.isAllowedForCollab(
            ResourceType.TASK,
            OperationType.DELETE,
            this.chosenCollaborationService.collaboration$.value
          );
          this.canCreate = this.permissionService.isAllowedForCollab(
            ResourceType.TASK,
            OperationType.CREATE,
            this.chosenCollaborationService.collaboration$.value
          );
          this.canKill = this.permissionService.isAllowedForCollab(
            ResourceType.EVENT,
            OperationType.SEND,
            this.chosenCollaborationService.collaboration$.value
          );
        }
      });
  }
}
