import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { GetStoreRoleParameters, StoreRole, StoreRoleCreate, StoreRoleForm, StoreRoleLazyProperties } from '../models/api/store-role.model';
import { Pagination } from '../models/api/pagination.model';
import { getLazyProperties } from '../helpers/api.helper';

@Injectable({
  providedIn: 'root'
})
export class StoreRoleService {
  constructor(private apiService: ApiService) {}

  async getRoles(store_url: string): Promise<StoreRole[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<StoreRole>>(store_url, '/role', { per_page: 9999 });
    return result.data;
  }

  async getPaginatedRoles(store_url: string, currentPage: number, parameters?: GetStoreRoleParameters): Promise<Pagination<StoreRole>> {
    const result = await this.apiService.getForAlgorithmApiWithPagination<StoreRole>(store_url, `/role`, currentPage, {
      ...parameters
    });
    return result;
  }

  async getRole(store_url: string, id: string, lazyProperties: StoreRoleLazyProperties[]): Promise<StoreRole> {
    const result = await this.apiService.getForAlgorithmApi<StoreRole>(store_url, `/role/${id}`);

    const role = { ...result, users: [] };
    await getLazyProperties(result, role, lazyProperties, this.apiService, store_url);

    return role;
  }

  async createRole(store_url: string, roleForm: StoreRoleForm): Promise<StoreRole> {
      const roleCreate: StoreRoleCreate = {
        ...roleForm
      };
      return await this.apiService.postForAlgorithmApi<StoreRole>(store_url, `/role`, roleCreate);
    }

  async patchRole(store_url: string, role: StoreRole): Promise<StoreRole | null> {
    try {
          const requestBody: StoreRoleForm = {
            name: role.name,
            description: role.description,
            rules: role.rules.map((rule) => rule.id)
          };
          return await this.apiService.patchForAlgorithmApi<StoreRole>(store_url, `/role/${role.id}`, requestBody);
        } catch {
          return null;
        }
  }

  async deleteRole(store_url: string, roleID: number): Promise<void> {
    await this.apiService.deleteForAlgorithmApi(store_url, `/role/${roleID}?delete_dependents=true`);
  }
}
