import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';
import { ResType } from 'src/app/shared/enum';

import { ModalService } from 'src/app/services/common/modal.service';
import { Resource } from 'src/app/shared/types';
import { BehaviorSubject } from 'rxjs';
import { Pagination } from 'src/app/interfaces/utils';

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

  protected list(params: any = {}): any {
    return this.http.get(environment.api_url + '/' + this.resource_type, {
      params: params,
      observe: 'response',
    });
  }

  protected get(id: number): any {
    return this.http.get(
      environment.api_url + '/' + this.resource_type + '/' + id
    );
  }

  update(resource: Resource) {
    const data = this.get_data(resource);
    return this.http.patch<any>(
      environment.api_url + '/' + resource.type + '/' + resource.id,
      data
    );
  }

  create(resource: Resource) {
    const data = this.get_data(resource);
    return this.http.post<any>(environment.api_url + '/' + resource.type, data);
  }

  delete(resource: Resource, params: any = {}) {
    return this.http.delete<any>(
      environment.api_url + '/' + resource.type + '/' + resource.id,
      { params: params}
    );
  }

  abstract get_data(resource: any): any;

  get_total_number_resources(): number {
    return this.total_resource_count.value;
  }

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

  async getResources(
    convertJsonFunc: Function,
    pagination: Pagination,
    additionalConvertArgs: Resource[][] = [],
    request_params: any = {}
  ): Promise<Resource[]> {
    // get data of resources that logged-in user is allowed to view
    if (pagination.page) request_params['page'] = pagination.page;
    if (pagination.page_size) request_params['per_page'] = pagination.page_size;

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
    if (pagination.all_pages) {
      let page = pagination.page ? pagination.page : 1;
      while (json_data.links['next']) {
        page = page + 1;
        request_params['page'] = page;
        response = await this.list(request_params).toPromise();
        json_data = response.body;
        for (let dic of json_data.data) {
          resources.push(convertJsonFunc(dic, ...additionalConvertArgs));
        }
      }
    }

    this.resource_list.next(resources);
    return this.resource_list.value;
  }
}
