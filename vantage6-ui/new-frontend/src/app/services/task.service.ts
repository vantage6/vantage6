import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { BaseTask, CreateTask, Task, TaskLazyProperties } from '../models/api/task.models';
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

  async getTask(id: string, lazyProperties: TaskLazyProperties[] = []): Promise<Task> {
    const result = await this.apiService.getForApi<BaseTask>(`/task/${id}`, { include: 'results' });

    const task: Task = { ...result, init_org: undefined, init_user: undefined };
    await Promise.all(
      (lazyProperties as string[]).map(async (lazyProperty) => {
        if (!(result as any)[lazyProperty]) return;

        if ((result as any)[lazyProperty].link) {
          const resultProperty = await this.apiService.getForApi<any>((result as any)[lazyProperty].link);
          (task as any)[lazyProperty] = resultProperty;
        } else {
          const resultProperty = await this.apiService.getForApi<Pagination<any>>((result as any)[lazyProperty] as string);
          (task as any)[lazyProperty] = resultProperty.data;
        }
      })
    );

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

  async create(createTask: CreateTask): Promise<BaseTask> {
    return await this.apiService.postForApi<BaseTask>('/task', createTask);
  }
}
