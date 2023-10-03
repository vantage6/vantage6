import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Pagination } from '../models/api/pagination.model';
import {
  BaseOrganization,
  GetOrganizationParameters,
  Organization,
  OrganizationCreate,
  OrganizationLazyProperties
} from '../models/api/organization.model';
import { Role } from '../models/api/role.model';
import { getLazyProperties } from '../helpers/api.helper';

@Injectable({
  providedIn: 'root'
})
export class OrganizationService {
  constructor(private apiService: ApiService) {}

  async getOrganizations(parameters?: GetOrganizationParameters): Promise<BaseOrganization[]> {
    //TODO: Add backend no pagination instead of page size 9999
    const result = await this.apiService.getForApi<Pagination<BaseOrganization>>('/organization', { ...parameters, per_page: 9999 });
    return result.data;
  }

  async getPaginatedOrganizations(currentPage: number, parameters?: GetOrganizationParameters): Promise<Pagination<BaseOrganization>> {
    const result = await this.apiService.getForApiWithPagination<BaseOrganization>(`/organization`, currentPage, parameters);
    return result;
  }

  async getOrganization(id: string, lazyProperties: OrganizationLazyProperties[] = []): Promise<Organization> {
    const result = await this.apiService.getForApi<BaseOrganization>(`/organization/${id}`);

    const organization: Organization = { ...result, nodes: [], collaborations: [] };
    await getLazyProperties(result, organization, lazyProperties, this.apiService);

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

  async editOrganization(organizationID: string, organization: OrganizationCreate): Promise<BaseOrganization | null> {
    try {
      return await this.apiService.patchForApi<BaseOrganization>(`/organization/${organizationID}`, organization);
    } catch {
      return null;
    }
  }
}
