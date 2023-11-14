import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import {
  BaseTask,
  ColumnRetrievalInput,
  ColumnRetrievalResult,
  CreateTask,
  GetTaskParameters,
  Task,
  TaskLazyProperties
} from '../models/api/task.models';
import { Pagination } from '../models/api/pagination.model';
import { getLazyProperties } from '../helpers/api.helper';
import { mockDataCrossTabTemplateTask, mockDataQualityTemplateTask } from '../pages/template-task/create/mock';
import { TemplateTask } from '../models/api/templateTask.models';
import { isTaskFinished } from '../helpers/task.helper';

@Injectable({
  providedIn: 'root'
})
export class TaskService {
  constructor(private apiService: ApiService) {}

  async getTasks(currentPage: number, parameters?: GetTaskParameters): Promise<Pagination<BaseTask>> {
    const result = await this.apiService.getForApiWithPagination<BaseTask>(`/task`, currentPage, parameters);
    return result;
  }

  async getTask(id: number, lazyProperties: TaskLazyProperties[] = []): Promise<Task> {
    const result = await this.apiService.getForApi<BaseTask>(`/task/${id}`, { include: 'results,runs' });

    const task: Task = { ...result, init_org: undefined, init_user: undefined };
    await getLazyProperties(result, task, lazyProperties, this.apiService);

    //Handle base64 input
    if (Array.isArray(task.runs) && task.runs.length > 0) {
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
    }

    return task;
  }

  async createTask(createTask: CreateTask): Promise<BaseTask> {
    return await this.apiService.postForApi<BaseTask>('/task', createTask);
  }

  async deleteTask(id: number): Promise<void> {
    return await this.apiService.deleteForApi(`/task/${id}`);
  }

  async getTemplateTasks(): Promise<TemplateTask[]> {
    //TODO: Remove mock data when template tasks are implemented in backend
    return [mockDataQualityTemplateTask, mockDataCrossTabTemplateTask];
  }

  async getColumnNames(columnRetrieve: ColumnRetrievalInput): Promise<ColumnRetrievalResult> {
    return await this.apiService.postForApi<ColumnRetrievalResult>(`/column`, columnRetrieve);
  }

  async waitForResults(id: number): Promise<Task> {
    let task = await this.getTask(id);
    while (!isTaskFinished(task)) {
      // poll at an interval until task is finished
      await new Promise((resolve) => setTimeout(resolve, 2000));
      task = await this.getTask(id);
    }
    return task;
  }
}
