/* eslint-disable @typescript-eslint/no-explicit-any */
import { Pipe, PipeTransform } from '@angular/core';

export enum RunStatus {
  Killed = 'killed by user',
  StartFailed = 'start failed',
  Crashed = 'crashed',
  NotAllowed = 'not allowed',
  NoDockerImage = 'non-existing Docker image',
  Failed = 'failed',
  Active = 'active',
  Initializing = 'initializing',
  Pending = 'pending',
  Completed = 'completed'
}

@Pipe({
  name: 'orderByTaskStatus',
  standalone: true
})
export class OrderByTaskStatusPipe implements PipeTransform {
  transform(list: unknown, property: string, direction?: 'asc' | 'desc'): any[] {
    const statusOrder = Object.values(RunStatus);
    if (!Array.isArray(list)) {
      return [];
    }
    list.sort((a: any, b: any) => {
      if (statusOrder.indexOf(a[property]) < statusOrder.indexOf(b[property])) {
        return -1;
      } else if (statusOrder.indexOf(a[property]) > statusOrder.indexOf(b[property])) {
        return 1;
      } else {
        return 0;
      }
    });
    return direction === 'desc' ? list.reverse() : list;
  }
}
