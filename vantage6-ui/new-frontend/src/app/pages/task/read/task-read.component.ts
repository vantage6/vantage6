import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { getChipTypeForStatus, getStatusInfoTypeForStatus, getTaskStatusTranslation } from 'src/app/helpers/task.helper';
import { Algorithm, AlgorithmFunction, Output } from 'src/app/models/api/algorithm.model';
import { Task, TaskLazyProperties, TaskRun, TaskStatus, TaskResult } from 'src/app/models/api/task.models';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { TaskService } from 'src/app/services/task.service';
import { LogDialogComponent } from '../../../components/dialogs/log/log-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { Router } from '@angular/router';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { FormControl } from '@angular/forms';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { Subject, Subscription, takeUntil, timer } from 'rxjs';
import { FileService } from 'src/app/services/file.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { AlgorithmStatusChangeMsg } from 'src/app/models/socket-messages.model';

@Component({
  selector: 'app-task-read',
  templateUrl: './task-read.component.html',
  styleUrls: ['./task-read.component.scss']
})
export class TaskReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';

  destroy$ = new Subject();
  waitTaskComplete$ = new Subject();
  routes = routePaths;

  visualization = new FormControl(0);

  task: Task | null = null;
  algorithm: Algorithm | null = null;
  function: AlgorithmFunction | null = null;
  selectedOutput: Output | null = null;
  isLoading = true;
  canDelete = false;

  private taskStatusUpdateSubscription?: Subscription;

  constructor(
    public dialog: MatDialog,
    private router: Router,
    private translateService: TranslateService,
    private taskService: TaskService,
    private algorithmService: AlgorithmService,
    private chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService,
    private fileService: FileService,
    private socketioConnectService: SocketioConnectService
  ) {}

  async ngOnInit(): Promise<void> {
    this.canDelete = this.permissionService.isAllowedForCollab(
      ResourceType.TASK,
      OperationType.DELETE,
      this.chosenCollaborationService.collaboration$.value
    );
    this.visualization.valueChanges.subscribe((value) => {
      this.selectedOutput = this.function?.output?.[value || 0] || null;
    });
    await this.initData();
    this.taskStatusUpdateSubscription = this.socketioConnectService
      .getAlgorithmStatusUpdates()
      .subscribe((statusUpdate: AlgorithmStatusChangeMsg | null) => {
        if (statusUpdate) this.onAlgorithmStatusUpdate(statusUpdate);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
    this.waitTaskComplete$.next(true);
    this.taskStatusUpdateSubscription?.unsubscribe();
  }

  async initData(): Promise<void> {
    this.task = await this.taskService.getTask(Number.parseInt(this.id), [TaskLazyProperties.InitOrg, TaskLazyProperties.InitUser]);
    this.algorithm = await this.algorithmService.getAlgorithmByUrl(this.task.image);
    this.function = this.algorithm?.functions.find((_) => _.name === this.task?.input?.method) || null;
    this.selectedOutput = this.function?.output?.[0] || null;
    this.isLoading = false;
  }

  getChipTypeForStatus(status: TaskStatus) {
    return getChipTypeForStatus(status);
  }

  getTaskStatusTranslation(status: TaskStatus) {
    return getTaskStatusTranslation(this.translateService, status);
  }

  getStatusInfoTypeForStatus(status: TaskStatus) {
    return getStatusInfoTypeForStatus(status);
  }

  isTaskInProgress(): boolean {
    if (!this.task) return false;
    if (this.task.runs.length <= 0) return false;
    if (this.task.results?.some((result) => result.result === null)) return true;
    if (this.task.runs.every((run) => run.status === TaskStatus.Completed)) return false;
    return true;
  }

  isFailedRun(status: TaskStatus): boolean {
    return (
      status === TaskStatus.Failed ||
      status === TaskStatus.Crashed ||
      status === TaskStatus.NoDockerImage ||
      status === TaskStatus.StartFailed
    );
  }

  isActiveRun(status: TaskStatus): boolean {
    return status === TaskStatus.Pending || status === TaskStatus.Initializing || status === TaskStatus.Active;
  }

  openLog(log: string): void {
    this.dialog.open(LogDialogComponent, {
      width: '80vw',
      data: {
        log: log
      }
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

  displayTextResult(result: object | undefined): string {
    if (result === undefined) return '';
    const textResult = JSON.stringify(result);
    if (textResult.length > 100) {
      return textResult.substring(0, 100) + '...';
    }
    return textResult;
  }

  downloadResult(result: TaskResult): void {
    const filename = `vantage6_result_${result.id}.txt`;
    const textResult = JSON.stringify(result.decoded_result);
    this.fileService.downloadTxtFile(textResult, filename);
  }

  private async onAlgorithmStatusUpdate(statusUpdate: AlgorithmStatusChangeMsg): Promise<void> {
    if (!this.task) return;
    if (statusUpdate.task_id !== this.task.id) return;

    // update the status of the runs
    const run = this.task.runs.find((r) => r.id === statusUpdate.run_id);
    if (run) {
      run.status = statusUpdate.status as TaskStatus;
    }

    // if the task is completed, we need to reload the task to get the results
    if (statusUpdate.status === TaskStatus.Completed) {
      // Task is completed but we need to wait for the results to be available
      // on the server. Poll every second until the results are available.
      timer(0, 1000)
        .pipe(takeUntil(this.waitTaskComplete$))
        .subscribe({
          next: () => {
            this.initData();
            if (!this.isTaskInProgress()) {
              // stop polling
              this.waitTaskComplete$.next(true);
            }
          }
        });
    }
  }
}
