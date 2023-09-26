import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Pagination } from '../models/api/pagination.model';
import {
  BaseOrganization,
  Organization,
  OrganizationCreate,
  OrganizationLazyProperties,
  OrganizationSortProperties
} from '../models/api/organization.model';
import { Role } from '../models/api/role.model';

@Injectable({
  providedIn: 'root'
})
export class OrganizationService {
  constructor(private apiService: ApiService) {}

  async getOrganizations(sortProperty: OrganizationSortProperties = OrganizationSortProperties.ID): Promise<BaseOrganization[]> {
    const result = await this.apiService.getForApi<Pagination<BaseOrganization>>('/organization', { sort: sortProperty });
    return result.data;
  }

  async getPaginatedOrganizations(currentPage: number): Promise<Pagination<BaseOrganization>> {
    const result = await this.apiService.getForApiWithPagination<BaseOrganization>(`/organization`, currentPage);
    return result;
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

  async getRolesForOrganization(organizationID: string): Promise<Role[]> {
    const result = await this.apiService.getForApi<Pagination<Role>>(`/role`, {
      organization_id: organizationID,
      include_root: true,
      sort: 'name'
    });
    const filteredRoles = result.data.filter((role) => role.name !== 'node' && role.name !== 'container');
    return filteredRoles;
  }

  async createOrganization(organization: OrganizationCreate): Promise<BaseOrganization | null> {
    try {
      return await this.apiService.postForApi<BaseOrganization>('/organization', organization);
    } catch {
      return null;
    }
  }
}
