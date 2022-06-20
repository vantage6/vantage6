import { Component, Input, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { ApiTaskService } from 'src/app/services/api/api-task.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { TaskDataService } from 'src/app/services/data/task-data.service';
import { BaseViewComponent } from '../../base/base-view/base-view.component';
import { Task, getEmptyTask } from 'src/app/interfaces/task';
import { ResType } from 'src/app/shared/enum';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { Organization } from 'src/app/interfaces/organization';

@Component({
  selector: 'app-task-view',
  templateUrl: './task-view.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './task-view.component.scss',
  ],
})
export class TaskViewComponent extends BaseViewComponent implements OnInit {
  @Input() task: Task = getEmptyTask();
  @Input() org_id: number = -1;

  constructor(
    public userPermission: UserPermissionService,
    protected apiTaskService: ApiTaskService,
    protected taskDataService: TaskDataService,
    protected modalService: ModalService
  ) {
    super(apiTaskService, taskDataService, modalService);
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
