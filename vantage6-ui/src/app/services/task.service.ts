import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import {
  BaseTask,
  ColumnRetrievalInput,
  ColumnRetrievalResult,
  CreateTask,
  GetTaskParameters,
  KillTask,
  Task,
  TaskLazyProperties,
  TaskResult
} from 'src/app/models/api/task.models';
import { Pagination } from 'src/app/models/api/pagination.model';
import { getLazyProperties } from 'src/app/helpers/api.helper';
// import { mockDataCrossTabTemplateTask, mockDataQualityTemplateTask } from '../pages/analyze/template-task/create/mock';
// import { TemplateTask } from 'src/app/models/api/templateTask.models';
import { isTaskFinished } from 'src/app/helpers/task.helper';
import { SnackbarService } from './snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { ChosenCollaborationService } from './chosen-collaboration.service';
import { EncryptionService } from './encryption.service';

@Injectable({
  providedIn: 'root'
})
export class TaskService {
  constructor(
    private apiService: ApiService,
    private snackBarService: SnackbarService,
    private translateService: TranslateService,
    private chosenCollaborationService: ChosenCollaborationService,
    private encryptionService: EncryptionService
  ) {}

  async getTasks(parameters?: GetTaskParameters): Promise<BaseTask[]> {
    const result = await this.apiService.getForApi<Pagination<BaseTask>>('/task', { ...parameters, per_page: 9999 });
    return result.data;
  }

  async getPaginatedTasks(currentPage: number, parameters?: GetTaskParameters): Promise<Pagination<BaseTask>> {
    const result = await this.apiService.getForApiWithPagination<BaseTask>(`/task`, currentPage, parameters);
    return result;
  }

  async getTask(id: number, lazyProperties: TaskLazyProperties[] = []): Promise<Task> {
    const result = await this.apiService.getForApi<BaseTask>(`/task/${id}`, { include: 'results,runs' });

    const task: Task = { ...result, init_org: undefined, init_user: undefined };
    await getLazyProperties(result, task, lazyProperties, this.apiService);

    //Handle base64 input
    if (Array.isArray(task.runs) && task.runs.length > 0) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let input: any = undefined;
      try {
        input = this.getDecodedInput(task.runs[0].input);
      } catch (e) {
        this.snackBarService.showMessage(this.translateService.instant('task.alert-failed-read-input'));
      }
      // TODO this may not always true: what if different runs have different inputs?
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
    if (Array.isArray(task.results) && task.results.length > 0) {
      for (const result of task.results) {
        if (result.result) {
          // often, the parsed result is a stringified JSON object
          try {
            result.decoded_result = this.getDecodedResult(result);
          } catch (e) {
            this.snackBarService.showMessage(this.translateService.instant('task.alert-failed-read-result'));
          }
        }
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

  async killTask(id: number): Promise<void> {
    const killTaskParams: KillTask = { id: id };
    await this.apiService.postForApi('/kill/task', killTaskParams);
  }

  // async getTemplateTasks(): Promise<TemplateTask[]> {
  //   //TODO: Remove mock data when template tasks are implemented in backend
  //   return [mockDataQualityTemplateTask, mockDataCrossTabTemplateTask];
  // }

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

  private getDecodedResult(taskResult: TaskResult): object | undefined {
    if (!taskResult.result) return undefined;
    // decrypt result
    let decryptedResult: string;
    if (this.chosenCollaborationService.isEncrypted()) {
      decryptedResult = this.encryptionService.decryptData(taskResult.result);
    } else {
      // if not decrypted, just decode it
      decryptedResult = atob(taskResult.result);
    }
    // decode result
    const decodedResult = JSON.parse(decryptedResult);
    if (typeof decodedResult === 'string') {
      return JSON.parse(decodedResult);
    }
    return decodedResult;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private getDecodedInput(taskRunInput: string): any {
    let decryptedInput: string;
    if (this.chosenCollaborationService.isEncrypted()) {
      decryptedInput = this.encryptionService.decryptData(taskRunInput);
    } else {
      decryptedInput = atob(taskRunInput);
    }
    // decode input
    return JSON.parse(decryptedInput);
  }
}
