import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

import { Resource } from 'src/app/shared/types';
import { removeMatchedIdFromArray } from 'src/app/shared/utils';
import { ApiService } from '../api/api.service';
import { ConvertJsonService } from '../common/convert-json.service';

@Injectable({
  providedIn: 'root',
})
export abstract class BaseDataService {
  resource_single = new BehaviorSubject<Resource | null>(null);
  resource_list = new BehaviorSubject<Resource[]>([]);

  constructor(
    protected apiService: ApiService,
    protected convertJsonService: ConvertJsonService
  ) {}

  set(resource: Resource) {
    this.resource_single.next(resource);
  }

  async get(
    id: number,
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Observable<Resource | null>> {
    if (force_refresh) {
      this.resource_single.next(
        await this.apiService.getResource(
          id,
          convertJsonFunc,
          additionalConvertArgs
        )
      );
      return this.resource_single.asObservable();
    } else if (
      this.resource_single.value !== null &&
      this.resource_single.value.id === id
    ) {
      return this.resource_single.asObservable();
    } else {
      for (let r of this.resource_list.value) {
        if (r.id === id) {
          this.resource_single.next(r);
          return this.resource_single.asObservable();
        }
      }
      this.resource_single.next(
        await this.apiService.getResource(
          id,
          convertJsonFunc,
          additionalConvertArgs
        )
      );
      return this.resource_single.asObservable();
    }
  }

  async list(
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Observable<Resource[]>> {
    if (force_refresh || !this.hasListStored()) {
      this.resource_list.next(
        await this.apiService.getResources(
          convertJsonFunc,
          additionalConvertArgs
        )
      );
    }
    return this.resource_list.asObservable();
  }

  add(resource: Resource): void {
    const updated_list = [...this.resource_list.value, resource];
    this.resource_list.next(updated_list);
  }

  remove(resource: Resource): void {
    this.resource_list.next(
      removeMatchedIdFromArray(this.resource_list.value, resource.id)
    );
  }

  hasListStored(): boolean {
    return this.resource_list.value.length > 0;
  }
}
