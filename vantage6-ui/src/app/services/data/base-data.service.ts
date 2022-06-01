import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

import { Resource } from 'src/app/shared/types';
import { getById, removeMatchedIdFromArray } from 'src/app/shared/utils';
import { ApiService } from '../api/api.service';
import { ConvertJsonService } from '../common/convert-json.service';

@Injectable({
  providedIn: 'root',
})
export abstract class BaseDataService {
  saved_single_resources: { [id: number]: Resource } = {};
  resource_list = new BehaviorSubject<Resource[]>([]);

  constructor(
    protected apiService: ApiService,
    protected convertJsonService: ConvertJsonService
  ) {}

  save(resource: Resource) {
    this.saved_single_resources[resource.id] = resource;
  }

  protected async get_base(
    id: number,
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Resource | null> {
    if (force_refresh) {
      return await this.apiService.getResource(
        id,
        convertJsonFunc,
        additionalConvertArgs
      );
    } else if (id in this.saved_single_resources) {
      return this.saved_single_resources[id];
    } else {
      const r = getById(this.resource_list.value, id);
      if (r !== undefined) return r;
      else
        return await this.apiService.getResource(
          id,
          convertJsonFunc,
          additionalConvertArgs
        );
    }
  }

  protected async list_base(
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
