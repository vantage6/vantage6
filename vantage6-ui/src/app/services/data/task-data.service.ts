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
    return (await super.get_base(
      id,
      this.convertJsonService.getTask,
      force_refresh
    )) as Observable<Task>;
  }

  async list(force_refresh: boolean = false): Promise<Observable<Task[]>> {
    return (await super.list_base(
      this.convertJsonService.getTask,
      force_refresh
    )) as Observable<Task[]>;
  }

  async org_list(
    organization_id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Task[]>> {
    return (await super.org_list_base(
      organization_id,
      this.convertJsonService.getTask,
      force_refresh
    )) as Observable<Task[]>;
  }

  async collab_list(
    collaboration_id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Task[]>> {
    return (await super.collab_list_base(
      collaboration_id,
      this.convertJsonService.getTask,
      force_refresh
    )) as Observable<Task[]>;
  }

  save(task: Task) {
    // remove organization and collaboration properties - these should be set
    // within components where needed to prevent endless loop of updates
    if (task.initiator) task.initiator = undefined;
    if (task.collaboration) task.collaboration = undefined;
    super.save(task);
  }

  remove(task: Task): void {
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
    console.log(data);
    let tasks = this.resource_list.value;
    console.log(tasks);
    for (let task of tasks as Task[]) {
      if (task.id === data.task_id) {
        task.status = data.status;
        break;
      }
    }
    this.resource_list.next(tasks);
  }

  addNewTaskOnSocketEvent(data: any): void {
    if (data.task_id) this.get(data.task_id);
  }
}
