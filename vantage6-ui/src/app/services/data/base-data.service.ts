import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';

import { Resource } from 'src/app/shared/types';
import {
  addOrReplace,
  arrayContains,
  arrayContainsObjWithId,
  filterArrayByProperty,
  getIdsFromArray,
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

      // update the observables per org
      this.updateObsPerOrg(resources);

      // update observables that are gotten one by one
      this.updateObsById(resources);

      // update the observables per collab
      this.updateObsPerCollab(resources);

      // update the observables per page
      this.updateObsPerPage(resources);
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

  updateObsPerOrg(resources: Resource[]) {
    if (!this.requested_org_lists) return;
    if (resources.length && !('organization_id' in resources[0])) {
      // ignore resources that do not have organization ids -> we can not
      // divide them in resources per organization
      return;
    }
    for (let org_id of this.requested_org_lists) {
      if (org_id in this.resources_per_org) {
        this.resources_per_org[org_id].next(
          filterArrayByProperty(resources, 'organization_id', org_id)
        );
      } else {
        this.resources_per_org[org_id] = new BehaviorSubject<Resource[]>(
          filterArrayByProperty(resources, 'organization_id', org_id)
        );
      }
    }
  }

  updateObsById(resources: Resource[]) {
    for (let res of resources) {
      if (res.id in this.resources_by_id) {
        this.resources_by_id[res.id].next(res);
      } else {
        this.resources_by_id[res.id] = new BehaviorSubject<Resource | null>(
          res
        );
      }
    }
  }

  updateObsPerCollab(resources: Resource[]) {
    // TODO update to include only stuff from requested collabs
    if (resources.length && !('collaboration_id' in resources[0])) {
      return;
    }
    let col_ids = unique(getIdsFromArray(resources, 'collaboration_id'));
    for (let col_id of col_ids) {
      if (col_id in this.resources_per_col) {
        this.resources_per_col[col_id].next(
          filterArrayByProperty(resources, 'collaboration_id', col_id)
        );
      } else {
        this.resources_per_col[col_id] = new BehaviorSubject<Resource[]>(
          filterArrayByProperty(resources, 'collaboration_id', col_id)
        );
      }
    }
  }

  updateObsPerPage(resources: Resource[]) {
    for (let page_id in this.resources_by_pagination) {
      let page_resources = this.resources_by_pagination[page_id];
      for (let page_resource of page_resources.value) {
        if (arrayContainsObjWithId(page_resource.id, resources)) {
          page_resources.next(
            addOrReplace(page_resources.value, page_resource)
          );
        }
      }
    }
  }

  protected async get_base(
    id: number,
    convertJsonFunc: Function,
    force_refresh: boolean = false
  ): Promise<Observable<Resource | null>> {
    if (force_refresh || !(id in this.resources_by_id)) {
      let additional_resources = await this.getDependentResources();
      let resource = await this.apiService.getResource(
        id,
        convertJsonFunc,
        additional_resources
      );
      if (resource !== null) {
        this.save(resource);
      } else {
        // resource not found: create Observable with null value
        this.resources_by_id[id] = new BehaviorSubject<Resource | null>(null);
      }
    }
    return this.resources_by_id[id].asObservable();
  }

  protected async list_base(
    convertJsonFunc: Function,
    pagination: Pagination,
    force_refresh: boolean = false
  ): Promise<Observable<Resource[]>> {
    let page_id = getPageId(pagination);
    if (
      force_refresh ||
      !this.has_queried_list ||
      !(pagination.all_pages || page_id in this.resources_by_pagination)
    ) {
      let additional_resources = await this.getDependentResources();
      const resources = await this.apiService.getResources(
        convertJsonFunc,
        pagination,
        additional_resources
      );
      if (pagination.all_pages) {
        this.has_queried_list = true;
      } else {
        if (!(page_id in this.resources_by_pagination)) {
          // create empty observable as organization had not yet been queried
          this.resources_by_pagination[page_id] = new BehaviorSubject<
            Resource[]
          >(resources);
        }
      }
      this.saveMultiple(resources);
    }
    return pagination.all_pages
      ? this.resource_list.asObservable()
      : this.resources_by_pagination[page_id].asObservable();
  }

  async list_with_params_base(
    convertJsonFunc: Function,
    request_params: any,
    pagination: Pagination,
    save: boolean = true
  ): Promise<Resource[]> {
    // TODO we may want to transform this also to a function that yields observables
    let additional_resources = await this.getDependentResources();
    // TODO find a way to detect if this query was sent before, now it is
    // always repeated
    const resources = await this.apiService.getResources(
      convertJsonFunc,
      pagination,
      additional_resources,
      request_params
    );
    if (save) this.saveMultiple(resources);
    return resources;
  }

  async org_list_base(
    organization_id: number,
    convertJsonFunc: Function,
    pagination: Pagination,
    force_refresh: boolean = false,
    params: any = {}
  ): Promise<Observable<Resource[]>> {
    let page_id = getPageId(pagination);
    if (!arrayContains(this.requested_org_lists, organization_id)) {
      this.requested_org_lists.push(organization_id);
    }
    // check if we need to get resources for the current organization
    if (
      force_refresh ||
      !(organization_id in this.resources_per_org) ||
      !this.requested_org_pages.includes(pagination)
    ) {
      if (!(organization_id in this.resources_per_org)) {
        // create empty observable as organization had not yet been queried
        this.resources_per_org[organization_id] = new BehaviorSubject<
          Resource[]
        >([]);
      }
      let additional_resources = await this.getDependentResources();
      params['organization_id'] = organization_id;
      let org_resources = await this.apiService.getResources(
        convertJsonFunc,
        pagination,
        additional_resources,
        params
      );
      // save the new resources. This will also update the observables
      // for the list by organization.
      this.saveMultiple(org_resources);
      // save page
      if (!(page_id in this.resources_by_pagination)) {
        // create empty observable as organization had not yet been queried
        this.resources_by_pagination[page_id] = new BehaviorSubject<Resource[]>(
          org_resources
        );
      }
    }
    return pagination.all_pages
      ? this.resources_per_org[organization_id].asObservable()
      : this.resources_by_pagination[page_id].asObservable();
  }

  async collab_list_base(
    collaboration_id: number,
    convertJsonFunc: Function,
    pagination: Pagination,
    force_refresh: boolean = false
  ): Promise<Observable<Resource[]>> {
    let page_id = getPageId(pagination);
    if (
      force_refresh ||
      !(collaboration_id in this.resources_per_col) ||
      !this.requested_org_pages.includes(pagination)
    ) {
      if (!(collaboration_id in this.resources_per_col)) {
        // create empty observable as organization had not yet been queried
        this.resources_per_col[collaboration_id] = new BehaviorSubject<
          Resource[]
        >([]);
      }
      let additional_resources = await this.getDependentResources();
      let resources = await this.apiService.getResources(
        convertJsonFunc,
        pagination,
        additional_resources,
        { collaboration_id: collaboration_id }
      );
      // save the new resources. This will also update the observables
      // for the list per collaboration
      this.saveMultiple(resources);
      // save page
      if (!(page_id in this.resources_by_pagination)) {
        // create empty observable as organization had not yet been queried
        this.resources_by_pagination[page_id] = new BehaviorSubject<Resource[]>(
          resources
        );
      }
    }
    return pagination.all_pages
      ? this.resources_per_col[collaboration_id].asObservable()
      : this.resources_by_pagination[page_id].asObservable();
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
}
