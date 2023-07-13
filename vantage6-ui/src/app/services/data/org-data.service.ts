import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Organization } from 'src/app/interfaces/organization';
import { Pagination, defaultFirstPage, allPages } from 'src/app/interfaces/utils';
import { OrganizationApiService } from 'src/app/services/api/organization-api.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';

/**
 * Service for retrieving and updating organization data.
 */
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
    /**
     * Get an organization by id. If the organization is not in the cache,
     * it will be requested from the vantage6 server.
     *
     * @param id The id of the organization to get.
     * @param force_refresh Whether to force a refresh of the cache.
     * @returns An observable of the organization.
     */
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
    /**
     * Get all organizations. If the organizations are not in the cache,
     * they will be requested from the vantage6 server.
     *
     * @param force_refresh Whether to force a refresh of the cache.
     * @param pagination The pagination parameters to use.
     * @returns An observable of the organizations.
     */
    return (await super.list_base(
      this.convertJsonService.getOrganization,
      pagination,
      force_refresh
    )).asObservable() as Observable<Organization[]>;
  }

  async list_with_params(
    pagination: Pagination = allPages(),
    request_params: any = {}
  ): Promise<Observable<Organization[]>> {
    /**
     * Get all organizations with the given parameters. If the organizations
     * are not in the cache, they will be requested from the vantage6 server.
     *
     * @param pagination The pagination parameters to use.
     * @param request_params The parameters to use in the request.
     * @returns An observable of the organizations.
     */
    return (await super.list_with_params_base(
      this.convertJsonService.getOrganization,
      request_params,
      pagination,
    )).asObservable() as Observable<Organization[]>;
  }
}
