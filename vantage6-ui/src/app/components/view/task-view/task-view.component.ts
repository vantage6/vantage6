import { Component, Input, OnChanges, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { TaskApiService } from 'src/app/services/api/task-api.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { TaskDataService } from 'src/app/services/data/task-data.service';
import { BaseViewComponent } from '../base-view/base-view.component';
import { Task, getEmptyTask, EMPTY_TASK } from 'src/app/interfaces/task';
import { ResType, OpsType, ExitMode } from 'src/app/shared/enum';
import { Run } from 'src/app/interfaces/run';
import { RunDataService } from 'src/app/services/data/run-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { HttpClient } from '@angular/common/http';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-task-view',
  templateUrl: './task-view.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './task-view.component.scss',
  ],
})
export class TaskViewComponent
  extends BaseViewComponent
  implements OnInit, OnChanges
{
  @Input() task: Task = getEmptyTask();
  @Input() org_id: number = -1;
  runs: Run[] = [];

  constructor(
    public userPermission: UserPermissionService,
    protected taskApiService: TaskApiService,
    protected taskDataService: TaskDataService,
    protected modalService: ModalService,
    private runDataService: RunDataService,
    private orgDataService: OrgDataService,
    private http: HttpClient
  ) {
    super(taskApiService, taskDataService, modalService);
  }

  ngOnChanges() {
    if (this.task.id !== EMPTY_TASK.id) {
      this.setAlgorithmRuns();
    }
  }

  async setAlgorithmRuns(): Promise<void> {
    (await this.runDataService.get_by_task_id(this.task.id, true)).subscribe(
      (runs) => {
        // TODO the check below shouldn't be necessary but is added because
        // when switching back and forth between task pages 1, then 2, then 1,
        // and the observables of 2 are updated when we're back on page for task
        // 1, the values of 2 are showing (while we want to show 1)
        // The observables by task_id in the taskDataService however are fine...
        // I think it has to do with component loading, which is cached partially?
        if (runs.length > 0 && this.task.id !== runs[0].task_id) return;
        this.runs = runs;
        this.setResultOrganizations();
      }
    );
  }

  async setResultOrganizations(): Promise<void> {
    for (let r of this.runs) {
      if (r.organization_id) {
        (await this.orgDataService.get(r.organization_id)).subscribe((org) => {
          r.organization = org;
        });
      }
      //decrypt the result
      if (r.result) {
        // r.decrypted_result = atob(r.result);
        r.decrypted_result = atob(r.result).slice(5);
      }
    }
  }

  askConfirmDelete(): void {
    super.askConfirmDelete(this.task, ResType.TASK);
  }

  getCollaborationName(): string {
    return this.task.collaboration ? this.task.collaboration.name : '';
  }

  getInitOrgName(): string {
    return this.task.init_org ? this.task.init_org.name : '';
  }

  getInitUserName(): string {
    return this.task.init_user ? this.task.init_user.username : '';
  }

  getUserViewRouterLink(): string {
    return this.task.init_user
      ? `/user/view/${this.task.init_user_id}/${this.task.init_user.organization_id}`
      : '';
  }

  getDatabaseNames(): string {
    let databases = this.task.databases ? this.task.databases : ['default'];
    return databases.join(', ');
  }

  getRunPanelTitle(run: Run): string {
    let title = run.id.toString();
    if (run.organization) title += ` (${run.organization.name})`;
    return title;
  }

  canRepeatTask(): boolean {
    return (
      this.userPermission.can(OpsType.CREATE, ResType.TASK, this.org_id) &&
      this.task.parent_id === null
    );
  }

  askConfirmKill() {
    let task_kill_message = `task ${this.task.id}`;
    if (this.task.children_ids) {
      task_kill_message =
        task_kill_message +
        ` (and its ${this.task.children_ids.length} subtasks)`;
    }
    this.modalService
      .openKillModal(
        `You are about to send instructions to the node(s) executing this task to stop it.`,
        task_kill_message
      )
      .result.then((exit_mode) => {
        if (exit_mode === ExitMode.KILL) {
          this.kill();
        }
      });
  }

  kill() {
    // send kill request for this task
    this.http
      .post<any>(environment.api_url + '/kill/task', {
        id: this.task.id,
      })
      .subscribe(
        (data: any) => {
          this.modalService.openMessageModal([
            'The nodes have been instructed to kill this task!',
          ]);
          this.updateTaskAfterKill();
        },
        (error: any) => {
          this.modalService.openErrorModal(error.error.msg);
        }
      );
  }

  updateTaskAfterKill(): void {
    // update task after it has been killed by collecting it again from the
    // server
    this.taskDataService.get(this.task.id, true);
  }
}
