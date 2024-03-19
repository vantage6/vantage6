/* eslint-disable @typescript-eslint/no-explicit-any */
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'orderBy'
})
export class OrderByPipe implements PipeTransform {
  transform(list: unknown, property: string, direction?: 'asc' | 'desc'): any[] {
    if (!Array.isArray(list)) {
      return [];
    }
    list.sort((a: any, b: any) => {
      if (a[property] < b[property]) {
        return -1;
      } else if (a[property] > b[property]) {
        return 1;
      } else {
        return 0;
      }
    });
    return direction === 'desc' ? list.reverse() : list;
  }
}
