import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { BaseTask, CreateTask, GetTaskParameters, Task, TaskLazyProperties } from '../models/api/task.models';
import { Pagination } from '../models/api/pagination.model';
import { getLazyProperties } from '../helpers/api.helper';

@Injectable({
  providedIn: 'root'
})
export class TaskService {
  constructor(private apiService: ApiService) {}

  async getTasks(currentPage: number, parameters?: GetTaskParameters): Promise<Pagination<BaseTask>> {
    const result = await this.apiService.getForApiWithPagination<BaseTask>(`/task`, currentPage, parameters);
    return result;
  }

  async getTask(id: string, lazyProperties: TaskLazyProperties[] = []): Promise<Task> {
    const result = await this.apiService.getForApi<BaseTask>(
      `/task/${id}`, { include: 'results,runs' }
    );

    const task: Task = { ...result, init_org: undefined, init_user: undefined };
    await getLazyProperties(result, task, lazyProperties, this.apiService);

    //Handle base64 input
    const input = JSON.parse(atob(task.runs[0].input));
    if (input) {
      task.input = {
        method: input.method || '',
        parameters: input.kwargs
          ? Object.keys(input.kwargs).map((key) => {
              return {
                label: key,
                value: input.kwargs[key] || ''
              };
            })
          : []
      };
    }

    return task;
  }

  async createTask(createTask: CreateTask): Promise<BaseTask> {
    return await this.apiService.postForApi<BaseTask>('/task', createTask);
  }

  async deleteTask(id: number): Promise<void> {
    return await this.apiService.deleteForApi(`/task/${id}`);
  }
}
