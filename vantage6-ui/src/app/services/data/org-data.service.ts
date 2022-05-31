import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Organization } from 'src/app/interfaces/organization';
import { Resource } from 'src/app/shared/types';
import { ApiOrganizationService } from 'src/app/services/api/api-organization.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';

@Injectable({
  providedIn: 'root',
})
export class OrgDataService extends BaseDataService {
  constructor(
    protected apiService: ApiOrganizationService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async get(
    id: number,
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Observable<Organization>> {
    return (await super.get(
      id,
      convertJsonFunc,
      additionalConvertArgs,
      force_refresh
    )) as Observable<Organization>;
  }

  async list(
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Observable<Organization[]>> {
    return (await super.list(
      convertJsonFunc,
      additionalConvertArgs,
      force_refresh
    )) as Observable<Organization[]>;
  }
}
