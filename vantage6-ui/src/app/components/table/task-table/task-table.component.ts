import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import {
  deepcopy,
  filterArrayByProperty,
  getUniquePropertyValues,
  parseId,
} from 'src/app/shared/utils';
import { TableComponent } from '../base-table/table.component';
import { DisplayMode } from '../node-table/node-table.component';
import { Task } from 'src/app/interfaces/task';
import { TaskDataService } from 'src/app/services/data/task-data.service';
import { ExitMode, OpsType, ResType, ScopeType } from 'src/app/shared/enum';
import { Organization } from 'src/app/interfaces/organization';
import { ModalService } from 'src/app/services/common/modal.service';
import { TaskApiService } from 'src/app/services/api/task-api.service';
import { Resource } from 'src/app/shared/types';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { User } from 'src/app/interfaces/user';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { allPages } from 'src/app/interfaces/utils';

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

  TASK_STATUS_ALL: string = 'All';
  available_task_statues: string[] = [];
  selected_task_status: string = this.TASK_STATUS_ALL;
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
    'status',
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
    // TODO get only orgs and collabs involved in tasks?
    (await this.orgDataService.list(false, allPages())).subscribe((orgs) => {
      this.organizations = orgs;
    });

    (await this.collabDataService.list(false, allPages())).subscribe((cols) => {
      this.collaborations = cols;
    });

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

  async setup(force_refresh: boolean = false) {
    await this.setResources(force_refresh);

    this.setAvailableTaskStatuses();

    await this.addCollaborationsToResources();

    await this.addInitiatingOrgsToTasks();

    await this.addInitiatingUsersToTasks();

    this.dataSource.data = this.resources;

    this.modalService.closeLoadingModal();
  }

  protected async setResources(force_refresh: boolean = false) {
    if (this.displayMode === DisplayMode.ORG) {
      // if displaying tasks for a certain organization, display the tasks for
      // each collaboration that the organization is involved in
      this.resources = [];
      for (let collab_id of (this.current_organization as Organization)
        .collaboration_ids) {
        (
          await this.taskDataService.collab_list(collab_id, force_refresh)
        ).subscribe((tasks) => {
          this.resources = filterArrayByProperty(
            this.resources,
            'collaboration_id',
            collab_id,
            false
          );
          this.resources.push(...tasks);
        });
      }
    } else if (this.displayMode === DisplayMode.COL) {
      (
        await this.taskDataService.collab_list(
          this.route_org_id as number,
          force_refresh
        )
      ).subscribe((tasks) => {
        this.resources = tasks;
      });
    } else {
      (await this.taskDataService.list(force_refresh)).subscribe(
        (tasks: Task[]) => {
          this.resources = tasks;
        }
      );
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
        ResType.COLLABORATION,
        ScopeType.ANY
      )
    ) {
      entity = 'collaboration';
    }
    if (
      this.userPermission.hasPermission(
        OpsType.VIEW,
        ResType.ORGANIZATION,
        ScopeType.GLOBAL
      )
    ) {
      if (entity) entity += '/';
      entity += 'organization';
    }
    return `Select ${entity} to view:`;
  }

  getSelectedTaskStatus(): string {
    return this.selected_task_status;
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
        if (org.id === r.initiator_id) {
          r.init_org = org;
          break;
        }
      }
    }
  }

  protected async addInitiatingUsersToTasks() {
    (await this.userDataService.list(allPages())).subscribe((users) => {
      this.users = users;
      // add users to tasks
      for (let r of this.resources as Task[]) {
        for (let user of this.users) {
          if (user.id === r.init_user_id) {
            r.init_user = user;
            break;
          }
        }
      }
    });
  }

  setCurrentCollaboration(): void {
    for (let col of this.collaborations) {
      if (col.id === this.route_org_id) {
        this.current_collaboration = col;
        break;
      }
    }
  }

  getStatus(task: Task): string {
    if (task.status) {
      return task.status;
    } else {
      return task.complete ? 'Completed' : 'Unknown';
    }
  }

  async deleteSelectedTasks(): Promise<void> {
    for (let task of this.selection.selected) {
      this.taskApiService
        .delete(task)
        .toPromise()
        .then((data) => {
          this.taskDataService.remove(task as Task);
          // reinitialize table to reflect the deleted tasks
          this.setup();
          this.selection.clear();
        })
        .catch((error) => {
          this.modalService.openErrorModal(error.error.msg);
        });
    }
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
        !this.userPermission.can(
          OpsType.DELETE,
          ResType.TASK,
          task.initiator_id
        )
      ) {
        return false;
      }
    }
    return true;
  }

  canOnlyDeleteSubset(): boolean {
    return this.selection.selected.length > 0 && !this.canDeleteSelection();
  }

  filterTasks() {
    // filter tasks by current value of selected status and initiator
    let selection = [];
    // first filter by task status
    if (this.selected_task_status === this.TASK_STATUS_ALL) {
      selection = this.resources;
    } else {
      selection = filterArrayByProperty(
        this.resources,
        'status',
        this.selected_task_status
      );
    }
    // now filter by initiator
    if (this.task_initiator_selected === TaskInitator.ALL) {
      // pass: don't shrink selection further
    } else if (this.task_initiator_selected === TaskInitator.ORG) {
      let own_org_id = this.userPermission.user.organization_id;
      selection = selection.filter(function (elem: any) {
        return elem.initiator_id === own_org_id;
      });
    } else {
      // if show tasks initiated by user itself
      let own_user_id = this.userPermission.user.id;
      selection = selection.filter(function (elem: any) {
        return elem.init_user_id === own_user_id;
      });
    }
    // set new data selection
    this.dataSource.data = selection;
  }

  filterTaskStatus(selected_status: string = this.TASK_STATUS_ALL): void {
    this.selected_task_status = selected_status;
    this.filterTasks();
  }

  filterTasksByInitiator(initiator: TaskInitator) {
    this.task_initiator_selected = initiator;
    this.filterTasks();
  }

  async refreshTasks() {
    this.modalService.openLoadingModal();
    await this.setup(true);
    this.modalService.closeLoadingModal();
  }

  deleteResource(resource: Resource) {
    // table data should be reset because when a task is deleted, also children
    // and parent tasks are updated to reflect the deleted task
    this.setup();
  }

  setAvailableTaskStatuses() {
    this.available_task_statues = getUniquePropertyValues(
      this.resources,
      'status'
    );
  }

  getInitiatingUser(task: Task) {
    return task.init_user ? task.init_user.username : '<unknown>';
  }
}
