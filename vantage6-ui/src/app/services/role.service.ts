import { Injectable } from '@angular/core';
import { ApiService } from './api.service';

import { BaseRole, GetRoleParameters, Role, RoleCreate, RoleForm, RoleLazyProperties, RolePatch } from 'src/app/models/api/role.model';
import { Pagination } from 'src/app/models/api/pagination.model';
import { getLazyProperties } from 'src/app/helpers/api.helper';

@Injectable({
  providedIn: 'root'
})
export class RoleService {
  constructor(private apiService: ApiService) {}

  async getRoles(parameters?: GetRoleParameters): Promise<Role[]> {
    //TODO: Add backend no pagination instead of page size 9999
    const result = await this.apiService.getForApi<Pagination<Role>>('/role', { ...parameters, per_page: 9999 });
    return result.data;
  }

  async getPaginatedRoles(currentPage: number, parameters?: GetRoleParameters): Promise<Pagination<Role>> {
    const result = await this.apiService.getForApiWithPagination<Role>(`/role`, currentPage, parameters);
    return result;
  }

  async getRole(roleID: string, lazyProperties: RoleLazyProperties[] = []): Promise<Role> {
    const result = await this.apiService.getForApi<BaseRole>(`/role/${roleID}`);
    const role: Role = { ...result, rules: [], users: [] };
    await getLazyProperties(result, role, lazyProperties, this.apiService);

    return role;
  }

  async createRole(roleForm: RoleForm): Promise<Role> {
    const roleCreate: RoleCreate = {
      ...roleForm
    };
    return await this.apiService.postForApi<Role>(`/role`, roleCreate);
  }

  async deleteRole(roleID: number): Promise<boolean> {
    return await this.apiService.deleteForApi(`/role/${roleID}`);
  }

  async patchRole(role: Role): Promise<Role | null> {
    try {
      const requestBody: RolePatch = {
        name: role.name,
        description: role.description,
        rules: role.rules.map((rule) => rule.id)
      };
      return await this.apiService.patchForApi<Role>(`/role/${role.id}`, requestBody);
    } catch {
      return null;
    }
  }
}
