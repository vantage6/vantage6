import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

import {
  Resource,
  ResourceInCollab,
  ResourceInOrg,
} from 'src/app/shared/types';
import {
  addOrReplace,
  getById,
  removeMatchedIdFromArray,
} from 'src/app/shared/utils';
import { BaseApiService } from '../api/base-api.service';
import { ConvertJsonService } from '../common/convert-json.service';

@Injectable({
  providedIn: 'root',
})
export abstract class BaseDataService {
  resource_list: Resource[] = [];
  has_queried_list: boolean = false;
  queried_org_ids: number[] = [];
  queried_collab_ids: number[] = [];

  constructor(
    protected apiService: BaseApiService,
    protected convertJsonService: ConvertJsonService
  ) {}

  protected async get_base(
    id: number,
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Resource | null> {
    let resource: Resource | null;
    if (force_refresh) {
      resource = await this.apiService.getResource(
        id,
        convertJsonFunc,
        additionalConvertArgs
      );
      if (resource !== null) this.save(resource);
    } else {
      resource = getById(this.resource_list, id);
      if (resource === undefined) {
        resource = await this.apiService.getResource(
          id,
          convertJsonFunc,
          additionalConvertArgs
        );
        if (resource !== null) this.save(resource);
      }
    }
    return resource;
  }

  protected async list_base(
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Resource[]> {
    if (force_refresh || !this.has_queried_list) {
      const resources = await this.apiService.getResources(
        convertJsonFunc,
        additionalConvertArgs
      );
      this.has_queried_list = true;
      this.saveMultiple(resources);
    }
    return this.resource_list;
  }

  async list_with_params_base(
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    request_params: any,
    save: boolean = true
  ): Promise<Resource[]> {
    // TODO find a way to detect if this query was sent before, now it is
    // always repeated
    const resources = await this.apiService.getResources(
      convertJsonFunc,
      additionalConvertArgs,
      request_params
    );
    if (save) this.saveMultiple(resources);
    return resources;
  }

  async org_list_base(
    organization_id: number,
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false,
    params: any = {}
  ): Promise<Resource[]> {
    let org_resources: Resource[] = [];
    if (force_refresh || !this.queried_org_ids.includes(organization_id)) {
      params['organization_id'] = organization_id;
      org_resources = await this.apiService.getResources(
        convertJsonFunc,
        additionalConvertArgs,
        params
      );
      this.queried_org_ids.push(organization_id);
      this.saveMultiple(org_resources);
    } else {
      // this organization has been queried before: get matches from the saved
      // data
      for (let resource of this.resource_list) {
        if ((resource as ResourceInOrg).organization_id === organization_id) {
          org_resources.push(resource);
        }
      }
    }
    return org_resources;
  }

  async collab_list_base(
    collaboration_id: number,
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Resource[]> {
    let resources: Resource[] = [];
    if (force_refresh || !this.queried_collab_ids.includes(collaboration_id)) {
      resources = await this.apiService.getResources(
        convertJsonFunc,
        additionalConvertArgs,
        { collaboration_id: collaboration_id }
      );
      this.queried_collab_ids.push(collaboration_id);
      this.saveMultiple(resources);
    } else {
      // this organization has been queried before: get matches from the saved
      // data
      for (let resource of this.resource_list) {
        if (
          (resource as ResourceInCollab).collaboration_id === collaboration_id
        ) {
          resources.push(resource);
        }
      }
    }
    return resources;
  }

  public saveMultiple(resources: Resource[]) {
    for (let r of resources) {
      this.save(r);
    }
  }

  public save(resource: Resource): void {
    let updated_list = [...this.resource_list];
    updated_list = addOrReplace(updated_list, resource);
    this.resource_list = updated_list;
  }

  public remove(resource: Resource): void {
    this.resource_list = removeMatchedIdFromArray(
      this.resource_list,
      resource.id
    );
  }

  public clear(): void {
    this.has_queried_list = false;
    this.queried_org_ids = [];
    this.queried_collab_ids = [];
    this.resource_list = [];
  }
}
