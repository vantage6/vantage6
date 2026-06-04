import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { BaseTask, CreateTask, GetTaskParameters, KillTask, Task, TaskLazyProperties, TaskResult } from 'src/app/models/api/task.models';
import { Pagination } from 'src/app/models/api/pagination.model';
import { getLazyProperties } from 'src/app/helpers/api.helper';
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

    //Handle base64 input arguments
    if (Array.isArray(task.runs) && task.runs.length > 0) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const arguments_: any = this.getDecodedArguments(task.runs[0].arguments);
      if (arguments_) {
        task.arguments = arguments_
          ? Object.keys(arguments_).map((key: string) => {
              return {
                label: key,
                value: arguments_[key] || ''
              };
            })
          : [];
      }
    }
    if (Array.isArray(task.results) && task.results.length > 0) {
      for (const result of task.results) {
        if (result.result) {
          if (result.blob_storage_used) {
            this.snackBarService.showMessage(this.translateService.instant('task.alert-blob-read-result'));
            break;
          }
          const decodedResult = this.getDecodedResult(result);
          if (decodedResult) result.decoded_result = decodedResult;
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

  async killNodeTasks(nodeId: number): Promise<void> {
    const killTaskParams = { id: nodeId };
    await this.apiService.postForApi('/kill/node/tasks', killTaskParams);
  }

  // async getTemplateTasks(): Promise<TemplateTask[]> {
  //   //TODO: Remove mock data when template tasks are implemented in backend
  //   return [mockDataQualityTemplateTask, mockDataCrossTabTemplateTask];
  // }

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
    const isEncrypted = this.chosenCollaborationService.isEncrypted();
    const errorTranslationCode = isEncrypted ? 'task.alert-failed-read-encrypted-result' : 'task.alert-failed-read-result';
    // decrypt result
    let decryptedResult = taskResult.result;
    try {
      decryptedResult = isEncrypted ? this.encryptionService.decryptData(taskResult.result) : atob(taskResult.result);
    } catch (error) {
      this.snackBarService.showMessage(this.translateService.instant(errorTranslationCode));
      return;
    }
    // decode result
    let decodedResult;
    try {
      decodedResult = JSON.parse(decryptedResult);
    } catch (error) {
      this.snackBarService.showMessage(this.translateService.instant(errorTranslationCode));
    }
    return decodedResult;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private getDecodedArguments(taskRunArguments: string): any {
    let decryptedArguments = '';
    const isEncrypted = this.chosenCollaborationService.isEncrypted();
    try {
      decryptedArguments = isEncrypted ? this.encryptionService.decryptData(taskRunArguments) : atob(taskRunArguments);
    } catch (error) {
      this.snackBarService.showMessage(this.translateService.instant('task.alert-failed-read-arguments'));
      return;
    }
    // decode arguments
    let decodedArguments;
    try {
      decodedArguments = JSON.parse(decryptedArguments);
    } catch (error) {
      this.snackBarService.showMessage(this.translateService.instant('task.alert-failed-read-arguments'));
    }
    return decodedArguments;
  }
}
