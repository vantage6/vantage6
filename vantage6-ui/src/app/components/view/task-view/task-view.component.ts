import { Component, Input, OnChanges, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { TaskApiService } from 'src/app/services/api/task-api.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { TaskDataService } from 'src/app/services/data/task-data.service';
import { BaseViewComponent } from '../base-view/base-view.component';
import { Task, getEmptyTask, EMPTY_TASK } from 'src/app/interfaces/task';
import { ExitMode, ResType } from 'src/app/shared/enum';
import { Result } from 'src/app/interfaces/result';
import { ResultDataService } from 'src/app/services/data/result-data.service';
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
  results: Result[] = [];

  constructor(
    public userPermission: UserPermissionService,
    protected taskApiService: TaskApiService,
    protected taskDataService: TaskDataService,
    protected modalService: ModalService,
    private resultDataService: ResultDataService,
    private orgDataService: OrgDataService,
    private http: HttpClient
  ) {
    super(taskApiService, taskDataService, modalService);
  }

  ngOnChanges() {
    if (this.task.id !== EMPTY_TASK.id) {
      this.setResults();
    }
  }

  async setResults(): Promise<void> {
    this.results = await this.resultDataService.get_by_task_id(this.task.id);

    for (let r of this.results) {
      if (r.organization_id)
        (await this.orgDataService.get(r.organization_id)).subscribe((org) => {
          r.organization = org;
        });
    }
  }

  askConfirmDelete(): void {
    super.askConfirmDelete(this.task, ResType.TASK);
  }

  getCollaborationName(): string {
    return this.task.collaboration ? this.task.collaboration.name : '';
  }

  getInitiatorName(): string {
    return this.task.initiator ? this.task.initiator.name : '';
  }

  getDatabaseName(): string {
    return this.task.database ? this.task.database : 'default';
  }

  getResultPanelTitle(result: Result): string {
    let title = result.name ? result.name : result.id.toString();
    if (result.organization) title += ` (${result.organization.name})`;
    return title;
  }

  askConfirmKill() {
    this.modalService
      .openKillModal(
        `You are about to send instructions to the node(s) executing this task to stop it.`,
        `task ${this.task.id}`
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
        },
        (error: any) => {
          this.modalService.openErrorModal(error.error.msg);
        }
      );
  }
}
