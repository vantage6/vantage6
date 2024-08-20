import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Pagination } from 'src/app/models/api/pagination.model';
import {
  BaseOrganization,
  GetOrganizationParameters,
  Organization,
  OrganizationCreate,
  OrganizationLazyProperties,
  OrganizationSortProperties
} from 'src/app/models/api/organization.model';
import { Role } from 'src/app/models/api/role.model';
import { getLazyProperties } from 'src/app/helpers/api.helper';
import { PermissionService } from './permission.service';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';

@Injectable({
  providedIn: 'root'
})
export class OrganizationService {
  constructor(
    private apiService: ApiService,
    private permissionService: PermissionService
  ) {}

  async getAllowedOrganizations(resource: ResourceType, operation: OperationType): Promise<BaseOrganization[] | Organization[]> {
    if (this.permissionService.isAllowed(ScopeType.GLOBAL, resource, operation)) {
      return await this.getOrganizations({ sort: OrganizationSortProperties.Name });
    } else if (this.permissionService.isAllowed(ScopeType.COLLABORATION, resource, operation)) {
      return await this.getOrganizations({
        sort: OrganizationSortProperties.Name,
        ids: this.permissionService.activeUser?.permissions?.orgs_in_collabs
      });
    } else if (this.permissionService.isAllowed(ScopeType.ORGANIZATION, resource, operation)) {
      if (!this.permissionService.activeUser?.organization) return [];
      return [await this.getOrganization(this.permissionService.activeUser?.organization.id.toString())];
    } else {
      // no permissions found
      return [];
    }
  }

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

  async deleteOrganization(organizationID: string): Promise<void> {
    return await this.apiService.deleteForApi(`/organization/${organizationID}?delete_dependents=true`);
  }
}
