import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import {
  BaseTask,
  ColumnRetrievalInput,
  ColumnRetrievalResult,
  CreateTask,
  GetTaskParameters,
  Task,
  TaskLazyProperties,
  TaskStatus
} from '../models/api/task.models';
import { Pagination } from '../models/api/pagination.model';
import { getLazyProperties } from '../helpers/api.helper';
import { mockDataCrossTabTemplateTask, mockDataQualityTemplateTask } from '../pages/template-task/create/mock';
import { TemplateTask } from '../models/api/templateTask.models';

@Injectable({
  providedIn: 'root'
})
export class TaskService {
  constructor(private apiService: ApiService) {}

  async getTasks(currentPage: number, parameters?: GetTaskParameters): Promise<Pagination<BaseTask>> {
    const result = await this.apiService.getForApiWithPagination<BaseTask>(`/task`, currentPage, parameters);
    return result;
  }

  // TODO id should be a number
  async getTask(id: string, lazyProperties: TaskLazyProperties[] = []): Promise<Task> {
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

  async wait_for_results(id: number): Promise<Task> {
    let task = await this.getTask(id.toString());
    while (!this.hasFinished(task)) {
      // poll every second until task is finished
      await new Promise((resolve) => setTimeout(resolve, 1000));
      task = await this.getTask(id.toString());
    }
    return task;
  }

  private hasFinished(task: Task): boolean {
    return ![TaskStatus.Pending, TaskStatus.Initializing, TaskStatus.Active].includes(task.status);
  }
}
