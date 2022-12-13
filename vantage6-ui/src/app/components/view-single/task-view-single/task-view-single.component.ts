import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { EMPTY_ORGANIZATION } from 'src/app/interfaces/organization';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { EMPTY_TASK, getEmptyTask, Task } from 'src/app/interfaces/task';
import { ModalService } from 'src/app/services/common/modal.service';
import { UtilsService } from 'src/app/services/common/utils.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { TaskDataService } from 'src/app/services/data/task-data.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { ResType } from 'src/app/shared/enum';
import { BaseSingleViewComponent } from '../base-single-view/base-single-view.component';

@Component({
  selector: 'app-task-view-single',
  templateUrl: './task-view-single.component.html',
  styleUrls: ['./task-view-single.component.scss'],
})
export class TaskViewSingleComponent
  extends BaseSingleViewComponent
  implements OnInit
{
  route_id: number | null = null;
  task: Task = getEmptyTask();
  rules: Rule[] = [];
  roles: Role[] = [];
  organization_id: number = -1;

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    protected utilsService: UtilsService,
    private taskDataService: TaskDataService,
    private orgDataService: OrgDataService,
    private collabDataService: CollabDataService,
    private userDataService: UserDataService,
    protected modalService: ModalService
  ) {
    super(
      activatedRoute,
      userPermission,
      utilsService,
      ResType.TASK,
      modalService
    );
  }

  protected readRoute(): void {
    this.activatedRoute.paramMap.subscribe((params) => {
      this.route_id = this.utilsService.getId(params, ResType.TASK);
      this.organization_id = this.utilsService.getId(
        params,
        ResType.ORGANIZATION,
        'org_id'
      );
      if (
        this.route_id === EMPTY_TASK.id ||
        this.organization_id === EMPTY_ORGANIZATION.id
      ) {
        return; // cannot get task data
      }
      this.setup();
    });
  }

  async setResources() {
    await this.setTask();

    this.setSubResources();
  }

  setSubResources() {
    this.setInitiatingOrganization();

    this.setInitiatingUser();

    this.setCollaboration();
  }

  async setInitiatingOrganization() {
    (await this.orgDataService.get(this.task.initiator_id)).subscribe((org) => {
      this.task.init_org = org;
    });
  }

  async setInitiatingUser() {
    (await this.userDataService.get(this.task.init_user_id)).subscribe(
      (user) => {
        this.task.init_user = user;
      }
    );
  }

  async setCollaboration() {
    (await this.collabDataService.get(this.task.collaboration_id)).subscribe(
      (collab) => {
        this.task.collaboration = collab;
      }
    );
  }

  async setTask(): Promise<void> {
    (await this.taskDataService.get(this.route_id as number)).subscribe(
      (task) => {
        // TODO the check below shouldn't be necessary but is added because
        // when switching back and forth between task pages 1, then 2, then 1,
        // and the observables of 2 are updated when we're back on page for task
        // 1, the values of 2 are showing (while we want to show 1)
        // The observables by task_id in the taskDataService however are fine...
        // I think it has to do with component loading, which is cached partially?
        if (this.route_id !== task.id) return;
        this.task = task;
        this.setSubResources();
      }
    );
  }
}
