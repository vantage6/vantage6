import { TranslateService } from '@ngx-translate/core';
import { Task, TaskStatus, TaskStatusGroup } from 'src/app/models/api/task.models';

export const getChipTypeForStatus = (status: TaskStatus): 'default' | 'active' | 'success' | 'error' => {
  switch (status) {
    case TaskStatus.Initializing:
    case TaskStatus.Active:
      return 'active';
    case TaskStatus.Completed:
      return 'success';
    case TaskStatus.Failed:
    case TaskStatus.StartFailed:
    case TaskStatus.NoDockerImage:
    case TaskStatus.Crashed:
    case TaskStatus.Killed:
    case TaskStatus.NotAllowed:
    case TaskStatus.Unknown:
      return 'error';
    default:
      return 'default';
  }
};

export const getTaskStatusTranslation = (translateService: TranslateService, status: TaskStatus) => {
  const statusKey = Object.keys(TaskStatus)[Object.values(TaskStatus).indexOf(status)];
  const translationKey = `task-status.${statusKey}`;
  const translation = translateService.instant(translationKey);
  if (translation === translationKey) {
    return status;
  }
  return translation;
};

export const getStatusType = (status: TaskStatus): TaskStatusGroup => {
  switch (status) {
    case TaskStatus.Initializing:
    case TaskStatus.Active:
      return TaskStatusGroup.Active;
    case TaskStatus.Completed:
      return TaskStatusGroup.Success;
    case TaskStatus.Failed:
    case TaskStatus.StartFailed:
    case TaskStatus.NoDockerImage:
    case TaskStatus.Crashed:
    case TaskStatus.NotAllowed:
    case TaskStatus.Killed:
    case TaskStatus.Unknown:
      return TaskStatusGroup.Error;
    default:
      return TaskStatusGroup.Pending;
  }
};

export const isTaskFinished = (task: Task): boolean => {
  return ![TaskStatus.Pending, TaskStatus.Initializing, TaskStatus.Active].includes(task.status);
};
