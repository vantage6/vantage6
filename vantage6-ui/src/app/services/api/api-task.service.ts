import { Injectable } from '@angular/core';
import { ResType } from 'src/app/shared/enum';
import { ApiService } from './api.service';
import { Task } from 'src/app/interfaces/task';
import { HttpClient } from '@angular/common/http';
import { ModalService } from '../common/modal.service';

@Injectable({
  providedIn: 'root',
})
export class ApiTaskService extends ApiService {
  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.TASK, http, modalService);
  }

  get_data(task: Task): any {
    let data: any = {
      name: task.name,
      description: task.description,
      image: task.image,
      collaboration_id: task.collaboration_id,
      run_id: task.run_id,
      parent_id: task.parent_id,
      database: task.database,
      initiator_id: task.initiator_id,
      complete: task.complete,
    };
    return data;
  }
}
