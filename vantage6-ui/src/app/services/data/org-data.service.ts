import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Organization } from 'src/app/interfaces/organization';
import { OrganizationApiService } from 'src/app/services/api/organization-api.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';

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

  async get(id: number, force_refresh: boolean = false): Promise<Organization> {
    return (await super.get_base(
      id,
      this.convertJsonService.getOrganization,
      [],
      force_refresh
    )) as Organization;
  }

  async list(
    force_refresh: boolean = false
  ): Promise<Observable<Organization[]>> {
    return (await super.list_base(
      this.convertJsonService.getOrganization,
      [],
      force_refresh
    )) as Observable<Organization[]>;
  }

  async collab_list(collaboration_id: number, force_refresh: boolean = false) {
    let orgs: Organization[] = [];
    if (force_refresh || !this.queried_collab_ids.includes(collaboration_id)) {
      orgs = (await this.apiService.getResources(
        this.convertJsonService.getOrganization,
        [],
        { collaboration_id: collaboration_id }
      )) as Organization[];
      this.queried_collab_ids.push(collaboration_id);
      this.saveMultiple(orgs);
    } else {
      // this organization has been queried before: get matches from the saved
      // data
      for (let org of this.resource_list.value as Organization[]) {
        if (org.collaboration_ids.includes(collaboration_id)) {
          orgs.push(org);
        }
      }
    }
    return orgs;
  }
}
