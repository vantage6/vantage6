import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';

import { Resource } from 'src/app/shared/types';
import {
  addOrReplace,
  arrayContains,
  arrayContainsObjWithId,
  filterArrayByProperty,
  getById,
  getIdsFromArray,
  objectEquals,
  removeMatchedIdFromArray,
  unique,
} from 'src/app/shared/utils';
import { BaseApiService } from '../api/base-api.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { Pagination, getPageId, getPageSize } from 'src/app/interfaces/utils';

@Injectable({
  providedIn: 'root',
})
export abstract class BaseDataService {
  resource_list = new BehaviorSubject<Resource[]>([]);
  resources_by_params: { [params: string]: BehaviorSubject<Resource[]> } = {};
  resources_per_org: { [org_id: number]: BehaviorSubject<Resource[]> } = {};
  resources_per_col: { [col_id: number]: BehaviorSubject<Resource[]> } = {};
  resources_by_id: { [id: number]: BehaviorSubject<Resource | null> } = {};
  resources_by_pagination: { [page_id: string]: BehaviorSubject<Resource[]> } =
    {};
  // TODO this boolean should depend on how many resources there are in total
  // in the database
  has_queried_list: boolean = false;
  // this variable saves which organization lists have been requested explicitly
  requested_org_lists: number[] = [];
  requested_col_pages: Pagination[] = [];
  requested_org_pages: Pagination[] = [];
  // track total number of resources
  total_resource_count: number = 0;

  constructor(
    protected apiService: BaseApiService,
    protected convertJsonService: ConvertJsonService
  ) {
    this.resource_list.subscribe((resources) => {
      // When the list of all resources is updated, ensure that sublists of
      // observables are also updated

      // update observables that are gotten one by one
      this.updateObsById(resources);

      // update the observables per params
      this.updateObsPerParams(resources);
    });
  }

  get_total_number_resources(): number {
    // TODO I think this goes wrong if someone creates resources and then
    // deletes all of them: the count would be 0 again, but not in the API
    // service. Find a way around this.
    if (this.total_resource_count === 0) {
      // get the total number of resources from API service
      this.total_resource_count = this.apiService.get_total_number_resources();
    }
    return this.total_resource_count;
  }

  async getDependentResources(): Promise<Resource[][]> {
    // to be implemented optionally by children
    return [];
  }

  updateObsById(resources: Resource[]) {
    for (let res of resources) {
      if (!(res.id in this.resources_by_id)) {
        this.resources_by_id[res.id] = new BehaviorSubject<Resource | null>(
          res
        );
      } else if (!objectEquals(res, this.resources_by_id[res.id].value)){
        this.resources_by_id[res.id].next(res);
      }
    }
  }

  updateObsPerParams(resources: Resource[]) {
    for (let params in this.resources_by_params) {
      let params_resources = this.resources_by_params[params];
      for (let params_resource of params_resources.value) {
        if (
          arrayContainsObjWithId(params_resource.id, resources) &&
          !objectEquals(params_resource, getById(resources, params_resource.id))
        ) {
          params_resources.next(
            addOrReplace(params_resources.value, params_resource)
          );
        }
      }
    }
  }

  protected async get_base(
    id: number,
    convertJsonFunc: Function,
    force_refresh: boolean = false
  ): Promise<BehaviorSubject<Resource | null>> {
    // TODO consider always returning BehaviorSubjects, in base functions?
    if (force_refresh || !(id in this.resources_by_id)) {
    //   let additional_resources = await this.getDependentResources();
      let resource = await this.apiService.getResource(
        id,
        convertJsonFunc
      );
      if (resource !== null) {
        this.save(resource);
      } else {
        // resource not found: create Observable with null value
        this.resources_by_id[id] = new BehaviorSubject<Resource | null>(null);
      }
    }
    return this.resources_by_id[id];
  }

  protected async list_base(
    convertJsonFunc: Function,
    pagination: Pagination,
    force_refresh: boolean = false,
    additional_params: any = {}
  ): Promise<BehaviorSubject<Resource[]>> {
    let result = this.list_with_params_base(
      convertJsonFunc, additional_params, pagination, force_refresh
    )
    if (pagination.all_pages) {
      this.has_queried_list = true;
    }
    return result;
  }

  async list_with_params_base(
    convertJsonFunc: Function,
    request_params: any,
    pagination: Pagination,
    force_refresh: boolean = false
  ): Promise<BehaviorSubject<Resource[]>> {
    if (pagination.page){
      request_params['page'] = pagination.page;
    }
    if (pagination.page_size){
      request_params['per_page'] = pagination.page_size;
    }

    let params_key: string = this.paramsKey(request_params);

    if (force_refresh || !(params_key in this.resources_by_params)) {
      // get any dependent resources that may be required
      let additional_resources = await this.getDependentResources();

      // get the resources
      const resources = await this.apiService.getResources(
        convertJsonFunc,
        pagination.all_pages,
        additional_resources,
        request_params
      );

      // store the resources in observable based on the params
      this.resources_by_params[params_key] =
        new BehaviorSubject<Resource[]>(resources);

      // save the resources in the general list
      this.saveMultiple(resources);
    }
    return this.resources_by_params[params_key];
  }

  async org_list_base(
    organization_id: number,
    convertJsonFunc: Function,
    pagination: Pagination,
    force_refresh: boolean = false,
    params: any = {}
  ): Promise<BehaviorSubject<Resource[]>> {
    params['organization_id'] = organization_id;
    return this.list_with_params_base(
      convertJsonFunc, params, pagination, force_refresh
    )
  }

  async collab_list_base(
    collaboration_id: number,
    convertJsonFunc: Function,
    pagination: Pagination,
    force_refresh: boolean = false
  ): Promise<Observable<Resource[]>> {
    let params: any = {collaboration_id: collaboration_id};
    return this.list_with_params_base(
      convertJsonFunc, params, pagination, force_refresh
    )
  }

  public saveMultiple(resources: Resource[]) {
    let updated_list = [...this.resource_list.value];
    for (let r of resources) {
      updated_list = addOrReplace(updated_list, r);
    }
    this.resource_list.next(updated_list);
  }

  public save(resource: Resource): void {
    // update general list
    let updated_list = [...this.resource_list.value];
    updated_list = addOrReplace(updated_list, resource);
    if (updated_list.length > this.resource_list.value.length) {
      // if this is new resource, increase the count
      this.total_resource_count += 1;
    }
    this.resource_list.next(updated_list);
    // update pagination lists
    for (let page_id in this.resources_by_pagination) {
      let page_resources = this.resources_by_pagination[page_id];
      if (arrayContainsObjWithId(resource.id, page_resources.value)) {
        let updated_page_resources = [...page_resources.value];
        updated_page_resources = addOrReplace(updated_page_resources, resource);
        this.resources_by_pagination[page_id].next(updated_page_resources);
      } else if (page_resources.value.length < getPageSize(page_id)) {
        let updated_page_resources = [...page_resources.value];
        updated_page_resources = addOrReplace(updated_page_resources, resource);
        this.resources_by_pagination[page_id].next(updated_page_resources);
      }
    }
  }

  public remove(resource: Resource): void {
    // remove from general list
    this.resource_list.next(
      removeMatchedIdFromArray(this.resource_list.value, resource.id)
    );
    // decrease count of resources
    this.total_resource_count -= 1;
    // remove from pagination lists
    for (let page_id in this.resources_by_pagination) {
      let page_resources = this.resources_by_pagination[page_id];
      if (arrayContainsObjWithId(resource.id, page_resources.value)) {
        this.resources_by_pagination[page_id].next(
          removeMatchedIdFromArray(
            this.resources_by_pagination[page_id].value,
            resource.id
          )
        );
      }
    }
  }

  public clear(): void {
    this.has_queried_list = false;
    this.resource_list.next([]);
  }

  private paramsKey(params: any): string {
    return JSON.stringify(params);
  }
}
