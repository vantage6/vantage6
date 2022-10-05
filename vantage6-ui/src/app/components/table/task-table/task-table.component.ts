import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { deepcopy, parseId } from 'src/app/shared/utils';
import { TableComponent } from '../base-table/table.component';
import { DisplayMode } from '../node-table/node-table.component';
import { EMPTY_TASK, Task } from 'src/app/interfaces/task';
import { TaskDataService } from 'src/app/services/data/task-data.service';
import { ExitMode, OpsType, ResType, ScopeType } from 'src/app/shared/enum';
import { Organization } from 'src/app/interfaces/organization';
import { ModalService } from 'src/app/services/common/modal.service';
import { TaskApiService } from 'src/app/services/api/task-api.service';
import { ModalMessageComponent } from '../../modal/modal-message/modal-message.component';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { User } from 'src/app/interfaces/user';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { Resource } from 'src/app/shared/types';

export enum TaskStatus {
  ALL = 'All',
  COMPLETE = 'Completed',
  INCOMPLETE = 'Not completed',
}

export enum TaskInitator {
  ALL = 'All',
  ORG = 'My organization',
  USER = 'Myself',
}

// TODO this contains a lot of duplication from NodeTableComponent, fix that
@Component({
  selector: 'app-task-table',
  templateUrl: './task-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../table/base-table/table.component.scss',
    './task-table.component.scss',
  ],
})
export class TaskTableComponent extends TableComponent implements OnInit {
  collaborations: Collaboration[] = [];
  users: User[] = [];
  rules: Rule[] = [];
  roles: Role[] = [];
  current_collaboration: Collaboration | null;
  displayMode = DisplayMode.ALL;
  task_statuses = TaskStatus;
  task_status_selected = TaskStatus.ALL as string;
  task_initiators = TaskInitator;
  task_initiator_selected = TaskInitator.ALL as string;

  displayedColumns: string[] = [
    'select',
    'id',
    'name',
    // 'description',
    'image',
    'collaboration',
    'init_org',
    'init_user',
    'complete',
  ];

  constructor(
    private router: Router,
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private orgDataService: OrgDataService,
    private collabDataService: CollabDataService,
    private taskDataService: TaskDataService,
    private taskApiService: TaskApiService,
    private userDataService: UserDataService,
    private ruleDataService: RuleDataService,
    private roleDataService: RoleDataService,
    protected modalService: ModalService
  ) {
    super(activatedRoute, userPermission, modalService);
  }

  async init(): Promise<void> {
    this.organizations = await this.orgDataService.list();

    this.collaborations = await this.collabDataService.list(this.organizations);

    this.readRoute();
  }

  ngAfterViewInit(): void {
    super.ngAfterViewInit();
    this.dataSource.sortingDataAccessor = (item: any, property: any) => {
      let sorter: any;
      if (property === 'init_org') {
        sorter = item.init_org.name;
      } else if (property === 'init_user') {
        sorter = item.init_user.name;
      } else if (property === 'collaboration') {
        sorter = item.collaboration.name;
      } else {
        sorter = item[property];
      }
      return this.sortBy(sorter);
    };
  }

  async readRoute() {
    if (this.router.url.includes('org')) {
      this.displayMode = DisplayMode.ORG;
    } else if (this.router.url.includes('collab')) {
      this.displayMode = DisplayMode.COL;
    } else {
      this.displayMode = DisplayMode.ALL;
    }

    this.activatedRoute.paramMap.subscribe((params: any) => {
      let id: any;
      if (this.displayMode === DisplayMode.ORG) {
        id = parseId(params.get('org_id'));
      } else if (this.displayMode === DisplayMode.COL) {
        id = parseId(params.get('collab_id'));
      }
      if (isNaN(id)) {
        this.route_org_id = null;
        this.current_organization = null;
        this.current_collaboration = null;
      } else {
        this.route_org_id = id;
        if (this.displayMode === DisplayMode.ORG) {
          this.setCurrentOrganization();
          this.current_collaboration = null;
        } else {
          this.setCurrentCollaboration();
          this.current_organization = null;
        }
      }
      this.setup();
    });
  }

  async setup() {
    await this.setResources();

    await this.addCollaborationsToResources();

    await this.addInitiatingOrgsToTasks();

    await this.addInitiatingUsersToTasks();

    this.dataSource.data = this.resources;

    this.modalService.closeLoadingModal();
  }

  protected async setResources() {
    if (this.displayMode === DisplayMode.ORG) {
      // if displaying tasks for a certain organization, display the tasks for
      // each collaboration that the organization is involved in
      this.resources = [];
      for (let collab_id of (this.current_organization as Organization)
        .collaboration_ids) {
        this.resources.push(
          ...(await this.taskDataService.collab_list(collab_id))
        );
      }
    } else if (this.displayMode === DisplayMode.COL) {
      this.resources = await this.taskDataService.collab_list(
        this.route_org_id as number
      );
    } else {
      this.resources = await this.taskDataService.list();
    }
    // make a copy to prevent that changes in these resources are directly
    // reflected in the resources within dataServices
    this.resources = deepcopy(this.resources);
  }

  getNameDropdown() {
    if (
      this.current_organization &&
      this.userPermission.hasPermission(
        OpsType.VIEW,
        ResType.ORGANIZATION,
        ScopeType.GLOBAL
      )
    )
      return this.current_organization.name;
    else if (this.current_collaboration) return this.current_collaboration.name;
    else return 'All';
  }

  getSelectDropdownText(): string {
    let entity: string = '';
    if (
      this.userPermission.hasPermission(
        OpsType.VIEW,
        ResType.ORGANIZATION,
        ScopeType.GLOBAL
      )
    ) {
      entity = 'organization';
    }
    if (
      this.userPermission.hasPermission(
        OpsType.VIEW,
        ResType.COLLABORATION,
        ScopeType.ANY
      )
    ) {
      if (entity) entity += '/';
      entity += 'collaboration';
    }
    return `Select ${entity} to view:`;
  }

  protected async addCollaborationsToResources() {
    for (let r of this.resources as Task[]) {
      for (let col of this.collaborations) {
        if (col.id === r.collaboration_id) {
          r.collaboration = col;
          break;
        }
      }
    }
  }

  protected async addInitiatingOrgsToTasks() {
    for (let r of this.resources as Task[]) {
      for (let org of this.organizations) {
        if (org.id === r.init_org_id) {
          r.init_org = org;
          break;
        }
      }
    }
  }

  protected async addInitiatingUsersToTasks() {
    // TODO it would be nice if we can simply get the users without needing
    // to get rules/roles first (this is currently done so users are stored
    // properly in the dataServices)
    this.rules = await this.ruleDataService.list();
    this.roles = await this.roleDataService.list(this.rules);
    this.users = await this.userDataService.list(this.roles, this.rules);
    for (let r of this.resources as Task[]) {
      for (let user of this.users) {
        if (user.id === r.init_user_id) {
          r.init_user = user;
          break;
        }
      }
    }
  }

  setCurrentCollaboration(): void {
    for (let col of this.collaborations) {
      if (col.id === this.route_org_id) {
        this.current_collaboration = col;
        break;
      }
    }
  }

  getCompletedText(task: Task) {
    return task.complete ? 'Yes' : 'No';
  }

  async deleteSelectedTasks(): Promise<void> {
    for (let task of this.selection.selected) {
      let data = this.taskApiService
        .delete(task)
        .toPromise()
        .catch((error) => {
          this.modalService.openMessageModal(ModalMessageComponent, [
            error.error.msg,
          ]);
        });
      this.taskDataService.remove(task);
    }
    // reinitialize table to reflect the deleted tasks
    this.setup();
    this.selection.clear();
  }

  askConfirmDelete(): void {
    // open modal window to ask for confirmation of irreversible delete action
    this.modalService
      .openDeleteModal(this.selection.selected, ResType.TASK)
      .result.then((exit_mode) => {
        if (exit_mode === ExitMode.DELETE) {
          this.deleteSelectedTasks();
        }
      });
  }

  canDeleteSelection(): boolean {
    // cannot delete if none selected
    if (this.selection.selected.length === 0) return false;
    // can delete if global delete rights
    if (
      this.userPermission.hasPermission(
        OpsType.DELETE,
        ResType.TASK,
        ScopeType.GLOBAL
      )
    )
      return true;
    // otherwise check if allowed to delete all individual tasks
    for (let task of this.selection.selected as Task[]) {
      if (
        !this.userPermission.can(OpsType.DELETE, ResType.TASK, task.init_org_id)
      ) {
        return false;
      }
    }
    return true;
  }

  canOnlyDeleteSubset(): boolean {
    return this.selection.selected.length > 0 && !this.canDeleteSelection();
  }

  filterTaskStatus(selected_status: string): void {
    // if showing all, set to all and return
    this.task_status_selected = selected_status;
    if (selected_status === TaskStatus.ALL) {
      this.dataSource.data = this.resources;
      return;
    }

    // else, filter resources by 'complete' or 'incomplete' tasks
    let show_complete = selected_status === TaskStatus.COMPLETE ? true : false;
    let resources_shown = this.resources.filter(function (elem: any) {
      return elem.complete === show_complete;
    });
    this.dataSource.data = resources_shown;
  }

  filterTasksByInitiator(initiator: TaskInitator) {
    this.task_initiator_selected = initiator;
    if (initiator === TaskInitator.ALL) {
      this.dataSource.data = this.resources;
    } else if (initiator === TaskInitator.ORG) {
      let own_org_id = this.userPermission.user.organization_id;
      this.dataSource.data = this.resources.filter(function (elem: any) {
        return elem.init_org_id === own_org_id;
      });
    } else {
      // if show tasks initiated by user itself
      let own_user_id = this.userPermission.user.id;
      this.dataSource.data = this.resources.filter(function (elem: any) {
        return elem.init_user_id === own_user_id;
      });
    }
  }
}
