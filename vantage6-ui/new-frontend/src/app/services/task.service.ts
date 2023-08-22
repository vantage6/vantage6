import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { BaseTask, CreateTask } from '../models/api/task.models';
import { Pagination } from '../models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class TaskService {
  constructor(private apiService: ApiService) {}

  async getTasks(currentPage: number): Promise<Pagination<BaseTask>> {
    const result = await this.apiService.getForApiWithPagination<BaseTask>('/task', currentPage);
    return result;
  }

  create(createTask: CreateTask) {
    return this.apiService.postForApi('/task', createTask);
  }
}
