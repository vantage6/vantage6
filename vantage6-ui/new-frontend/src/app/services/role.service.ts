import { Injectable } from '@angular/core';
import { ApiService } from './api.service';

import { BaseRole, GetRoleParameters, Role, RoleLazyProperties, RolePatch } from '../models/api/role.model';
import { Pagination } from '../models/api/pagination.model';
import { getLazyProperties } from '../helpers/api.helper';
import { Rule } from '../models/api/rule.model';

@Injectable({
  providedIn: 'root'
})
export class RoleService {
  constructor(private apiService: ApiService) {}

  async getRoles(parameters?: GetRoleParameters): Promise<Role[]> {
    //TODO: Add backend no pagination instead of page size 9999
    const result = await this.apiService.getForApi<Pagination<Role>>('/role', { ...parameters });
    return result.data;
  }

  async getRole(roleID: string, lazyProperties: RoleLazyProperties[] = []): Promise<Role> {
    const result = await this.apiService.getForApi<BaseRole>(`/role/${roleID}`);
    const role: Role = { ...result, rules: [], users: [] };
    await getLazyProperties(result, role, lazyProperties, this.apiService);

    return role;
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
