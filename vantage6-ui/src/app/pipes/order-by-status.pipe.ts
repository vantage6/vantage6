/* eslint-disable @typescript-eslint/no-explicit-any */
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'orderByTaskStatus'
})
export class OrderByTaskStatusPipe implements PipeTransform {
  transform(list: unknown, property: string, direction?: 'asc' | 'desc'): any[] {
    const statusOrder = ['killed by user', 'start failed', 'crashed',
      'not allowed', 'non-existing Docker image', 'failed', 'active',
      'initializing', 'pending', 'completed'];
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
