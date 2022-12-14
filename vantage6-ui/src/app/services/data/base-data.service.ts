import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { Collaboration } from 'src/app/interfaces/collaboration';

import { Resource } from 'src/app/shared/types';
import {
  addOrReplace,
  arrayContains,
  filterArrayByProperty,
  getIdsFromArray,
  removeMatchedIdFromArray,
  unique,
} from 'src/app/shared/utils';
import { BaseApiService } from '../api/base-api.service';
import { ConvertJsonService } from '../common/convert-json.service';

@Injectable({
  providedIn: 'root',
})
export abstract class BaseDataService {
  resource_list = new BehaviorSubject<Resource[]>([]);
  resources_per_org: { [org_id: number]: BehaviorSubject<Resource[]> } = {};
  resources_per_col: { [col_id: number]: BehaviorSubject<Resource[]> } = {};
  resources_by_id: { [id: number]: BehaviorSubject<Resource | null> } = {};
  has_queried_list: boolean = false;
  requested_org_lists: number[] = [];

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
    });
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
    // for (let num in this.resources_by_id) {
    //   console.log(num, this.resources_by_id[num].value);
    // }
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
    force_refresh: boolean = false
  ): Promise<Observable<Resource[]>> {
    if (force_refresh || !this.has_queried_list) {
      let additional_resources = await this.getDependentResources();
      const resources = await this.apiService.getResources(
        convertJsonFunc,
        additional_resources
      );
      this.has_queried_list = true;
      this.saveMultiple(resources);
    }
    // TODO why do we return an observable here? I think it is much easier
    // to just return the resources (they are stored in dataServices anyway)
    return this.resource_list.asObservable();
  }

  async list_with_params_base(
    convertJsonFunc: Function,
    request_params: any,
    save: boolean = true
  ): Promise<Resource[]> {
    // TODO we may want to transform this also to a function that yields observables
    let additional_resources = await this.getDependentResources();
    // TODO find a way to detect if this query was sent before, now it is
    // always repeated
    const resources = await this.apiService.getResources(
      convertJsonFunc,
      additional_resources,
      request_params
    );
    if (save) this.saveMultiple(resources);
    return resources;
  }

  async org_list_base(
    organization_id: number,
    convertJsonFunc: Function,
    force_refresh: boolean = false,
    params: any = {}
  ): Promise<Observable<Resource[]>> {
    if (!arrayContains(this.requested_org_lists, organization_id)) {
      this.requested_org_lists.push(organization_id);
    }
    // check if we need to get resources for the current organization
    if (force_refresh || !(organization_id in this.resources_per_org)) {
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
        additional_resources,
        params
      );
      // save the new resources. This will also update the observables
      // for the list by organization.
      this.saveMultiple(org_resources);
    }
    return this.resources_per_org[organization_id].asObservable();
  }

  async collab_list_base(
    collaboration_id: number,
    convertJsonFunc: Function,
    force_refresh: boolean = false
  ): Promise<Observable<Resource[]>> {
    if (force_refresh || !(collaboration_id in this.resources_per_col)) {
      if (!(collaboration_id in this.resources_per_col)) {
        // create empty observable as organization had not yet been queried
        this.resources_per_col[collaboration_id] = new BehaviorSubject<
          Resource[]
        >([]);
      }
      let additional_resources = await this.getDependentResources();
      let resources = await this.apiService.getResources(
        convertJsonFunc,
        additional_resources,
        { collaboration_id: collaboration_id }
      );
      // save the new resources. This will also update the observables
      // for the list per collaboration
      this.saveMultiple(resources);
    }
    return this.resources_per_col[collaboration_id].asObservable();
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
    this.resource_list.next(updated_list);
  }

  public remove(resource: Resource): void {
    this.resource_list.next(
      removeMatchedIdFromArray(this.resource_list.value, resource.id)
    );
  }

  public clear(): void {
    this.has_queried_list = false;
    this.resource_list.next([]);
  }
}
