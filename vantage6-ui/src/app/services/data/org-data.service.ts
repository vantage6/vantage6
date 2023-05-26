import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Organization } from 'src/app/interfaces/organization';
import { Pagination, defaultFirstPage, allPages } from 'src/app/interfaces/utils';
import { OrganizationApiService } from 'src/app/services/api/organization-api.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { Resource } from 'src/app/shared/types';

@Injectable({
  providedIn: 'root',
})
export class OrgDataService extends BaseDataService {
  constructor(
    protected apiService: OrganizationApiService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async get(
    id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Organization>> {
    return (
      await super.get_base(
        id,
        this.convertJsonService.getOrganization,
        force_refresh
      )
    ).asObservable() as Observable<Organization>;
  }

  async list(
    force_refresh: boolean = false,
    pagination: Pagination = defaultFirstPage()
  ): Promise<Observable<Organization[]>> {
    return (await super.list_base(
      this.convertJsonService.getOrganization,
      pagination,
      force_refresh
    )) as Observable<Organization[]>;
  }

  async list_with_params(
    pagination: Pagination = allPages(),
    request_params: any = {}
  ): Promise<Organization[]> {
    return await super.list_with_params_base(
      this.convertJsonService.getOrganization,
      request_params,
      pagination,
    ) as Organization[];
  }
}
