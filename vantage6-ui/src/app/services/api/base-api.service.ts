import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';
import { ResType } from 'src/app/shared/enum';

import { ModalService } from 'src/app/services/common/modal.service';
import { Resource } from 'src/app/shared/types';
import { BehaviorSubject, Observable } from 'rxjs';

/**
 * Base class for all api services. This class contains the basic functions
 * for getting, creating, updating and deleting resources.
 */
@Injectable({
  providedIn: 'root',
})
export abstract class BaseApiService {
  resource_type: ResType;
  resource_single = new BehaviorSubject<Resource | null>(null);
  resource_list = new BehaviorSubject<Resource[]>([]);
  total_resource_count = new BehaviorSubject<number>(0);

  constructor(
    resource_type: ResType,
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    this.resource_type = resource_type;
  }

  /**
   * Get a list of resources from the API.
   *
   * @param params The parameters to use in the request.
   */
  protected list(params: any = {}): any {
    return this.http.get(environment.api_url + '/' + this.resource_type, {
      params: params,
      observe: 'response',
    });
  }

  /**
   * Get a resource by id from the API.
   *
   * @param id The id of the resource to get.
   * @returns An observable for the request response.
   */
  protected get(id: number): any {
    return this.http.get(
      environment.api_url + '/' + this.resource_type + '/' + id
    );
  }

  /**
   * Update a resource in the API.
   *
   * @param resource The resource to update.
   * @returns An observable for the request response.
   */
  update(resource: Resource): Observable<any> {
    const data = this.get_data(resource);
    return this.http.patch<any>(
      environment.api_url + '/' + resource.type + '/' + resource.id,
      data
    );
  }

  /**
   * Create a resource via the API.
   *
   * @param resource The resource to create.
   * @returns An observable for the request response.
   */
  create(resource: Resource): Observable<any> {
    const data = this.get_data(resource);
    return this.http.post<any>(environment.api_url + '/' + resource.type, data);
  }

  /**
   * Delete a resource via the API.
   *
   * @param resource The resource to delete.
   * @param params The parameters to use in the request.
   * @returns An observable for the request response.
   */
  delete(resource: Resource, params: any = {}) {
    return this.http.delete<any>(
      environment.api_url + '/' + resource.type + '/' + resource.id,
      { params: params }
    );
  }

  abstract get_data(resource: any): any;

  /**
   * Get the total number of resources for the given resource type.
   *
   * @returns The total number of resources.
   */
  get_total_number_resources(): number {
    return this.total_resource_count.value;
  }

  /**
   * Get data for a single resource from the API and convert it to a
   * Resource object.
   *
   * @param id The id of the resource to get.
   * @param convertJsonFunc The function to use to convert the json to a
   * Resource object.
   * @param additionalConvertArgs Additional arguments to pass to the
   * convertJsonFunc.
   * @returns The resource.
   */
  async getResource(
    id: number,
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = []
  ): Promise<Resource | null> {
    let json: any;
    try {
      json = await this.get(id).toPromise();
      this.resource_single.next(
        convertJsonFunc(json, ...additionalConvertArgs)
      );
      return this.resource_single.value;
    } catch (error: any) {
      this.modalService.openErrorModal(error.error.msg, true);
      return null;
    }
  }

  /**
   * Get data for multiple resources from the API and convert them to
   * Resource objects.
   *
   * @param convertJsonFunc The function to use to convert the json to a
   * Resource object.
   * @param all_pages Whether to get data for all Pagination pages.
   * @param additionalConvertArgs Additional arguments to pass to the
   * convertJsonFunc.
   * @param request_params The parameters to use in the request.
   * @returns The resources.
   */
  async getResources(
    convertJsonFunc: Function,
    all_pages: boolean = false,
    additionalConvertArgs: Resource[][] = [],
    request_params: any = {}
  ): Promise<Resource[]> {
    if (all_pages){
        request_params['page'] = 1;
    }
    // get data of resources that logged-in user is allowed to view
    let response = await this.list(request_params).toPromise();

    // get total count of resources from the headers (not just for current page)
    this.total_resource_count.next(response.headers.get('total-count'));

    // convert json to Resource[]
    let json_data = response.body;
    let resources = [];
    for (let dic of json_data.data) {
      resources.push(convertJsonFunc(dic, ...additionalConvertArgs));
    }

    // if all pages are requested, get data of all pages
    if (all_pages) {
      let page = 2;
      while (json_data.links['next']) {
        request_params['page'] = page;
        response = await this.list(request_params).toPromise();
        json_data = response.body;
        for (let dic of json_data.data) {
          resources.push(convertJsonFunc(dic, ...additionalConvertArgs));
        }
        page = page + 1;
      }
    }

    this.resource_list.next(resources);
    return this.resource_list.value;
  }
}
