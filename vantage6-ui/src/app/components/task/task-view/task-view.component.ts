import { Component, Input, OnChanges, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ApiTaskService } from 'src/app/services/api/api-task.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { TaskDataService } from 'src/app/services/data/task-data.service';
import { BaseViewComponent } from '../../base/base-view/base-view.component';
import { Task, getEmptyTask, EMPTY_TASK } from 'src/app/interfaces/task';
import { ResType } from 'src/app/shared/enum';
import { Result } from 'src/app/interfaces/result';
import { ResultDataService } from 'src/app/services/data/result-data.service';

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
    protected apiTaskService: ApiTaskService,
    protected taskDataService: TaskDataService,
    protected modalService: ModalService,
    private resultDataService: ResultDataService
  ) {
    super(apiTaskService, taskDataService, modalService);
  }

  ngOnChanges() {
    if (this.task.id !== EMPTY_TASK.id) {
      this.setResults();
    }
  }

  async setResults(): Promise<void> {
    this.results = await this.resultDataService.get_by_task_id(this.task.id);
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
}
