import { Component, Input, OnChanges, OnInit } from '@angular/core';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { TaskApiService } from 'src/app/services/api/task-api.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { TaskDataService } from 'src/app/services/data/task-data.service';
import { BaseViewComponent } from '../base-view/base-view.component';
import { Task, getEmptyTask, EMPTY_TASK } from 'src/app/interfaces/task';
import { OpsType, ResType } from 'src/app/shared/enum';
import { Result } from 'src/app/interfaces/result';
import { ResultDataService } from 'src/app/services/data/result-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';

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
    private orgDataService: OrgDataService
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
      if (r.organization_id) {
        r.organization = await this.orgDataService.get(r.organization_id);
      }
      // try to decrypt the result
      try {
        let decrypted_result = atob(r.result);
        if (decrypted_result.startsWith('json.')) {
          r.decrypted_result = decrypted_result.slice(5);
        }
      } catch {
        // ignore: could not read result
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

  getDatabaseName(): string {
    return this.task.database ? this.task.database : 'default';
  }

  getResultPanelTitle(result: Result): string {
    let title = result.name ? result.name : result.id.toString();
    if (result.organization) title += ` (${result.organization.name})`;
    return title;
  }

  canRepeatTask(): boolean {
    return (
      this.userPermission.can(OpsType.CREATE, ResType.TASK, this.org_id) &&
      this.task.parent_id === null
    );
  }
}
