import { Injectable } from '@angular/core';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';
import { Task } from 'src/app/interfaces/task';
import { Observable } from 'rxjs';
import { TaskApiService } from '../api/task-api.service';
import {
  removeMatchedIdFromArray,
  removeValueFromArray,
} from 'src/app/shared/utils';
import { SocketioConnectService } from 'src/app/services/common/socketio-connect.service';
import {
  Pagination,
  allPages,
  defaultFirstPage,
} from 'src/app/interfaces/utils';

/**
 * Service for retrieving and updating task data.
 */
@Injectable({
  providedIn: 'root',
})
export class TaskDataService extends BaseDataService {
  constructor(
    protected apiService: TaskApiService,
    protected convertJsonService: ConvertJsonService,
    private socketConnectService: SocketioConnectService
  ) {
    super(apiService, convertJsonService);
    // subscribe to task changes
    this.socketConnectService
      .getAlgorithmStatusUpdates()
      .subscribe((update) => {
        this.updateTaskOnSocketEvent(update);
      });
    // subscribe to new tasks
    this.socketConnectService.getTaskCreatedUpdates().subscribe((update) => {
      this.addNewTaskOnSocketEvent(update);
    });
  }

  async get(
    id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Task>> {
    /**
     * Get a task by id. If the task is not in the cache, it will be requested
     * from the vantage6 server.
     *
     * @param id The id of the task to get.
     * @param force_refresh Whether to force a refresh of the cache.
     * @returns An observable of the task.
     */
    return (
      await super.get_base(id, this.convertJsonService.getTask, force_refresh)
    ).asObservable() as Observable<Task>;
  }

  async list(
    force_refresh: boolean = false,
    pagination: Pagination = defaultFirstPage()
  ): Promise<Observable<Task[]>> {
    /**
     * Get all tasks. If the tasks are not in the cache, they will be requested
     * from the vantage6 server.
     *
     * @param force_refresh Whether to force a refresh of the cache.
     * @param pagination The pagination parameters to use.
     * @returns An observable of the tasks.
     */
    return (await super.list_base(
      this.convertJsonService.getTask,
      pagination,
      force_refresh,
      // only show top-level tasks (i.e. not subtasks) created by user
      { is_user_created: 1 }
    )).asObservable() as Observable<Task[]>;
  }

  async org_list(
    organization_id: number,
    force_refresh: boolean = false,
    pagination: Pagination = allPages()
  ): Promise<Observable<Task[]>> {
    /**
     * Get all tasks for an organization. If the tasks are not in the cache,
     * they will be requested from the vantage6 server.
     *
     * @param organization_id The id of the organization to get the tasks for.
     * @param force_refresh Whether to force a refresh of the cache.
     * @param pagination The pagination parameters to use.
     * @returns An observable of the tasks.
     */
    return (await super.org_list_base(
      organization_id,
      this.convertJsonService.getTask,
      pagination,
      force_refresh
    )).asObservable() as Observable<Task[]>;
  }

  async collab_list(
    collaboration_id: number,
    force_refresh: boolean = false,
    pagination: Pagination = allPages()
  ): Promise<Observable<Task[]>> {
    /**
     * Get all tasks for a collaboration. If the tasks are not in the cache,
     * they will be requested from the vantage6 server.
     *
     * @param collaboration_id The id of the collaboration to get the tasks for.
     * @param force_refresh Whether to force a refresh of the cache.
     * @param pagination The pagination parameters to use.
     * @returns An observable of the tasks.
     */
    return (await super.collab_list_base(
      collaboration_id,
      this.convertJsonService.getTask,
      pagination,
      force_refresh
    )) as Observable<Task[]>;
  }

  async list_with_params(
    pagination: Pagination = allPages(),
    request_params: any = {}
  ): Promise<Observable<Task[]>> {
    /**
     * Get tasks with the given parameters. If the tasks are not in the cache,
     * they will be requested from the vantage6 server.
     *
     * @param pagination The pagination parameters to use.
     * @param request_params The parameters to use in the request.
     * @returns An observable of the tasks.
     */
    return (await super.list_with_params_base(
      this.convertJsonService.getTask,
      request_params,
      pagination,
    )).asObservable() as Observable<Task[]>;
  }

  save(task: Task) {
    /**
     * Save a task to the cache.
     *
     * @param task The task to save.
     */
    // remove organization and collaboration properties - these should be set
    // within components where needed to prevent endless loop of updates
    if (task.init_org) task.init_org = undefined;
    if (task.init_user) task.init_user = undefined;
    if (task.collaboration) task.collaboration = undefined;

    // check if task has been created via UI. Then keep storing that
    if (task.id in this.resources_by_id) {
      let current_val: Task = this.resources_by_id[task.id].value as Task;
      if (current_val.created_via_ui) {
        task.created_via_ui = current_val.created_via_ui;
      }
    }

    // save the task
    super.save(task);
  }

  remove(task: Task): void {
    /**
     * Remove a task from the cache.
     *
     * @param task The task to remove.
     */
    // remove the task also from its parent task and/or child tasks
    if (task.parent_id || task.children_ids.length) {
      let tasks: Task[] = this.resource_list.value as Task[];
      for (let t of tasks) {
        if (t.id === task.parent_id) {
          t.children_ids = removeValueFromArray(t.children_ids, task.id);
          if (t.children) {
            t.children = removeMatchedIdFromArray(t.children, task.id);
          }
        } else if (task.children_ids.includes(t.id)) {
          t.parent_id = null;
          t.parent = undefined;
        }
      }
      this.resource_list.next(tasks);
    }

    super.remove(task);
  }

  updateTaskOnSocketEvent(data: any): void {
    /**
     * Update a task based on a socket event.
     *
     * @param data The data to update the task with.
     * @param data.task_id The id of the task to update.
     * @param data.status The new status of the task.
     * @param data.parent_id The id of the parent task.
     */
    let tasks = this.resource_list.value;
    for (let task of tasks as Task[]) {
      if (task.id === data.task_id) {
        task.status = data.status;
        if (data.parent_id) task.parent_id = data.parent_id;
      } else if (
        data.parent_id &&
        task.id === data.parent_id &&
        !task.children_ids.includes(data.task_id)
      ) {
        task.children_ids.push(data.task_id);
      }
    }
    this.resource_list.next(tasks);
  }

  addNewTaskOnSocketEvent(data: any): void {
    /**
     * Add a new task to the cache based on a socket event.
     *
     * @param data The data to add the task with.
     * @param data.task_id The id of the task to add.
     */
    if (data.task_id) this.get(data.task_id);
  }
}
