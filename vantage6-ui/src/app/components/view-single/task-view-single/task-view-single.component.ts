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
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
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
    private ruleDataService: RuleDataService,
    private roleDataService: RoleDataService,
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

    await this.setInitiatingOrganization();

    await this.setInitiatingUser();

    await this.setCollaboration();
  }

  async setInitiatingOrganization() {
    this.task.init_org = await this.orgDataService.get(this.task.initiator_id);
  }

  async setInitiatingUser() {
    // TODO it's stupid we first need to get all rules and roles just to set
    // a user
    this.rules = await this.ruleDataService.list();
    this.roles = await this.roleDataService.list(this.rules);
    this.task.init_user = await this.userDataService.get(
      this.task.init_user_id,
      this.roles,
      this.rules
    );
  }

  async setCollaboration() {
    this.task.collaboration = await this.collabDataService.get(
      this.task.collaboration_id
    );
  }

  async setTask(): Promise<void> {
    this.task = await this.taskDataService.get(this.route_id as number);
  }
}
