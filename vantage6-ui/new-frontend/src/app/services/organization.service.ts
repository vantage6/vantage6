import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Pagination } from '../models/api/pagination.model';
import { BaseOrganization, Organization, OrganizationLazyProperties } from '../models/api/organization.model';

@Injectable({
  providedIn: 'root'
})
export class OrganizationService {
  constructor(private apiService: ApiService) {}

  async getOrganizations(): Promise<BaseOrganization[]> {
    const result = await this.apiService.getForApi<Pagination<BaseOrganization>>('/organization');
    return result.data;
  }

  async getOrganization(id: string, lazyProperties: OrganizationLazyProperties[] = []): Promise<Organization> {
    const result = await this.apiService.getForApi<BaseOrganization>(`/organization/${id}`);

    const organization: Organization = { ...result, nodes: [], collaborations: [] };

    await Promise.all(
      lazyProperties.map(async (lazyProperty) => {
        if (!result[lazyProperty]) return;

        const resultProperty = await this.apiService.getForApi<Pagination<any>>(result[lazyProperty]);
        organization[lazyProperty] = resultProperty.data;
      })
    );

    return organization;
  }
}
