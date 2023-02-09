import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';
import { ResType } from 'src/app/shared/enum';

import { ModalService } from 'src/app/services/common/modal.service';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
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

  delete(resource: Resource) {
    return this.http.delete<any>(
      environment.api_url + '/' + resource.type + '/' + resource.id
    );
  }

  abstract get_data(resource: any): any;

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

    let json_data = await this.list(request_params).toPromise();

    let resources = [];
    for (let dic of json_data['data']) {
      resources.push(convertJsonFunc(dic, ...additionalConvertArgs));
    }

    // if all pages are requested, get data of all pages
    if (pagination.all_pages) {
      let page = pagination.page ? pagination.page : 1;
      while (json_data['links']['next']) {
        page = page + 1;
        request_params['page'] = page;
        json_data = await this.list(request_params).toPromise();
        for (let dic of json_data['data']) {
          resources.push(convertJsonFunc(dic, ...additionalConvertArgs));
        }
      }
    }

    this.resource_list.next(resources);
    return this.resource_list.value;
  }
}
