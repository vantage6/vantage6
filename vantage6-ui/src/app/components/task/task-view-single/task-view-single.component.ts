import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { EMPTY_ORGANIZATION } from 'src/app/interfaces/organization';
import { EMPTY_TASK, getEmptyTask, Task } from 'src/app/interfaces/task';
import { UtilsService } from 'src/app/services/common/utils.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { TaskDataService } from 'src/app/services/data/task-data.service';
import { ResType } from 'src/app/shared/enum';

@Component({
  selector: 'app-task-view-single',
  templateUrl: './task-view-single.component.html',
  styleUrls: ['./task-view-single.component.scss'],
})
export class TaskViewSingleComponent implements OnInit {
  route_id: number | null = null;
  task: Task = getEmptyTask();
  organization_id: number = -1;

  constructor(
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private utilsService: UtilsService,
    private taskDataService: TaskDataService,
    private orgDataService: OrgDataService,
    private collabDataService: CollabDataService
  ) {}

  ngOnInit(): void {
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) {
        this.init();
      }
    });
  }

  async init() {
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

  async setup() {
    await this.setTask();

    await this.setInitiatingOrganization();

    await this.setCollaboration();
  }

  async setInitiatingOrganization() {
    this.task.initiator = await this.orgDataService.get(this.task.initiator_id);
  }

  async setCollaboration() {
    this.task.collaboration = await this.collabDataService.get(
      this.task.collaboration_id
    );
  }

  async setTask(): Promise<void> {
    this.task = await this.taskDataService.get(this.route_id as number);
  }

  goBackToPreviousPage() {
    this.utilsService.goToPreviousPage();
  }
}
