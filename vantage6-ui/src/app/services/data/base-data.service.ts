import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';

import { Resource } from 'src/app/shared/types';
import {
  addOrReplace,
  arrayContainsObjWithId,
  getById,
  objectEquals,
  removeMatchedIdFromArray,
} from 'src/app/shared/utils';
import { BaseApiService } from '../api/base-api.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { Pagination } from 'src/app/interfaces/utils';

/**
 * This is the base class for all data services. The data services are used to
 * handle the data that is retrieved from the API. Data is cached in the data
 * services, so that it can be retrieved quickly when needed.
 */
@Injectable({
  providedIn: 'root',
})
export abstract class BaseDataService {
  resource_list = new BehaviorSubject<Resource[]>([]);
  resources_by_params: { [params: string]: BehaviorSubject<Resource[]> } = {};
  resources_by_id: { [id: number]: BehaviorSubject<Resource | null> } = {};

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

  /**
   * Get the total number of resources of the current resource type in the
   * database.
   *
   * @returns The total number of resources of the current resource type in
   * the database.
   */
  // TODO I think this goes wrong if someone creates resources and then
  // deletes all of them: the count would be 0 again, but not in the API
  // service. Find a way around this.
  get_total_number_resources(): number {

    if (this.total_resource_count === 0) {
      // get the total number of resources from API service
      this.total_resource_count = this.apiService.get_total_number_resources();
    }
    return this.total_resource_count;
  }

  /**
   * Define which resources are required to be retrieved from the API before
   * the current resource can be retrieved.
   *
   * @returns A list of lists of resources that are required to be retrieved
   * from the API before the current resource can be retrieved.
   */
  async getDependentResources(): Promise<Resource[][]> {
    // to be implemented optionally by children
    return [];
  }

  /**
   * Update the observables per resource id, if the resource has been updated.
   *
   * @param resources The resources that have been updated.
   */
  updateObsById(resources: Resource[]): void {
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

  /**
   * Update the observables that were obtained with a certain set of
   * parameters, when a (subset of) resources has been updated.
   *
   * @param resources The resources that have been updated.
   */
  updateObsPerParams(resources: Resource[]): void {
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
      // check if new resources have to be added to the list
      for (let params in this.resources_by_params) {
        let param_obj = JSON.parse(params);
        let params_resources = this.resources_by_params[params];
        for (let resource of resources){
          if (!arrayContainsObjWithId(resource.id, params_resources.value)) {
            // check if new resource has to be added to the list
            // this is
            // 1. if organization id is in params and matches
            // 2. if collaboration id is in params and matches
            // 3. if complete list is requested
            if ((
              "collaboration_id" in resource && "collaboration_id" in param_obj
              && resource.collaboration_id === param_obj.collaboration_id
             ) || (
              "organization_id" in resource && "organization_id" in param_obj
              && resource.organization_id === param_obj.organization_id
             ) || (
              Object.keys(param_obj).length === 0
             )){
              params_resources.next(
                addOrReplace(params_resources.value, resource)
              );
            }
          }
        }
      }
    }
  }

  /**
   * Get a resource by its id. If the resource is not yet in the cache, it is
   * retrieved from the API. This function is called by the get function of
   * the child classes.
   *
   * @param id The id of the resource to be retrieved.
   * @param convertJsonFunc The function to convert the JSON API response to
   * the resource type.
   * @param force_refresh Whether to force a refresh of the resource, even if
   * it is already in the cache.
   * @returns A BehaviorSubject that contains the resource.
   */
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
        // resource not found: create BehaviorSubject with null value
        this.resources_by_id[id] = new BehaviorSubject<Resource | null>(null);
      }
    }
    return this.resources_by_id[id];
  }

  /**
   * Get a list of resources. If the resources are not yet in the cache, they
   * are retrieved from the API. This function is called by the list function
   * of the child classes.
   *
   * @param convertJsonFunc The function to convert the JSON API response to
   * the resource type.
   * @param pagination The pagination parameters to use for the request.
   * @param force_refresh Whether to force a refresh of the resources, even
   * if they are already in the cache.
   * @param additional_params Any additional parameters to use for the
   * request.
   */
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

  /**
   * Get a list of resources with certain parameters. If the resources are
   * not yet in the cache, they are retrieved from the API. This function is
   * called by the list_with_params function of the child classes.
   *
   * @param convertJsonFunc The function to convert the JSON API response to
   * the resource type.
   * @param request_params The parameters to use for the request.
   * @param pagination The pagination parameters to use for the request.
   * @param force_refresh Whether to force a refresh of the resources, even
   * if they are already in the cache.
   * @returns A BehaviorSubject that contains the resources.
   */
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

  /**
   * Get a list of resources that are linked to a certain organization. If
   * the resources are not yet in the cache, they are retrieved from the API.
   * This function is called by the org_list function of the child classes.
   *
   * @param organization_id The id of the organization to which the resources
   * should be linked.
   * @param convertJsonFunc The function to convert the JSON API response to
   * the resource type.
   * @param pagination The pagination parameters to use for the request.
   * @param force_refresh Whether to force a refresh of the resources, even
   * if they are already in the cache.
   * @param params Any additional parameters to use for the request.
   * @returns A BehaviorSubject that contains the resources.
   */
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

  /**
   * Get a list of resources that are linked to a certain collaboration. If
   * the resources are not yet in the cache, they are retrieved from the API.
   * This function is called by the collab_list function of the child
   * classes.
   *
   * @param collaboration_id The id of the collaboration to which the
   * resources should be linked.
   * @param convertJsonFunc The function to convert the JSON API response to
   * the resource type.
   * @param pagination The pagination parameters to use for the request.
   * @param force_refresh Whether to force a refresh of the resources, even
   * if they are already in the cache.
   * @returns A BehaviorSubject that contains the resources.
   */
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

  /**
   * Save multiple resources to the cache.
   *
   * @param resources The resources to save.
   */
  public saveMultiple(resources: Resource[]): void {
    let updated_list = [...this.resource_list.value];
    for (let r of resources) {
      updated_list = addOrReplace(updated_list, r);
    }
    this.resource_list.next(updated_list);
  }

  /**
   * Save a resource to the cache.
   *
   * @param resource The resource to save.
   */
  public save(resource: Resource): void {
    // update general list
    let updated_list = [...this.resource_list.value];
    updated_list = addOrReplace(updated_list, resource);
    if (updated_list.length > this.resource_list.value.length) {
      // if this is new resource, increase the count
      this.total_resource_count += 1;
    }
    this.resource_list.next(updated_list);
  }

  /**
   * Remove a resource from the cache.
   *
   * @param resource The resource to remove.
   */
  public remove(resource: Resource): void {
    // remove from general list
    this.resource_list.next(
      removeMatchedIdFromArray(this.resource_list.value, resource.id)
    );
    // decrease count of resources
    this.total_resource_count -= 1;
  }

  /**
   * Clear the cache.
   */
  public clear(): void {
    this.has_queried_list = false;
    this.resource_list.next([]);
  }

  /**
   * Create a key for the parameters, so that they can be used as a key in a
   * dictionary.
   *
   * @param params The parameters to create a key for.
   * @returns A key for the parameters.
   */
  private paramsKey(params: any): string {
    return JSON.stringify(params);
  }
}
