import { Injectable } from '@angular/core';
import { ResType } from 'src/app/shared/enum';
import { BaseApiService } from './base-api.service';
import { Task } from 'src/app/interfaces/task';
import { HttpClient } from '@angular/common/http';
import { ModalService } from '../common/modal.service';

/**
 * Service for interacting with the task endpoints of the API
 */
@Injectable({
  providedIn: 'root',
})
export class TaskApiService extends BaseApiService {
  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.TASK, http, modalService);
  }

  /**
   * Get data for creating a task in the API.
   *
   * @param task The task object to get the data for.
   * @returns A dictionary with the data for creating the task.
   */
  get_data(task: Task): any {
    if (!task.input || !task.organizations) {
      return; // this is only for creating tasks, which requires input
    }
    let collab_id = task.collaboration
      ? task.collaboration.id
      : task.collaboration_id;
    let input: any = {
      master: task.input.master,
      method: task.input.method,
      output_format: task.input.output_format,
    };
    if (task.input.args.length) {
      input['args'] = task.input.args;
    }
    if (task.input.kwargs.length) {
      let kwargs: any = {};
      for (let kwarg of task.input.kwargs) {
        kwargs[kwarg.key] = kwarg.value;
      }
      input['kwargs'] = kwargs;
    }

    let org_input: any[] = [];
    for (let org of task.organizations) {
      org_input.push({
        id: org.id,
        input: btoa(JSON.stringify(input)),
      });
    }

    let databases: string[] = task.databases;
    if (!databases) {
      databases = ['default'];
    } else {
      // delete any empty strings
      databases = databases.filter((db) => db);
    }

    // TODO add encryption option
    let data: any = {
      name: task.name,
      description: task.description,
      image: task.image,
      organizations: org_input,
      collaboration_id: collab_id,
      databases: databases,
    };
    return data;
  }
}
