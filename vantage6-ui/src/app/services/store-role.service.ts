import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { GetStoreRoleParameters, StoreRole, StoreRoleCreate, StoreRoleForm, StoreRoleLazyProperties } from '../models/api/store-role.model';
import { Pagination } from '../models/api/pagination.model';
import { getLazyProperties } from '../helpers/api.helper';
import { AlgorithmStore } from '../models/api/algorithmStore.model';

@Injectable({
  providedIn: 'root'
})
export class StoreRoleService {
  constructor(private apiService: ApiService) {}

  async getRoles(algoStore: AlgorithmStore): Promise<StoreRole[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<StoreRole>>(algoStore, '/role', { per_page: 9999 });
    return result.data;
  }

  async getPaginatedRoles(
    algoStore: AlgorithmStore,
    currentPage: number,
    parameters?: GetStoreRoleParameters
  ): Promise<Pagination<StoreRole>> {
    const result = await this.apiService.getForAlgorithmApiWithPagination<StoreRole>(algoStore, `/role`, currentPage, {
      ...parameters
    });
    return result;
  }

  async getRole(algoStore: AlgorithmStore, id: string, lazyProperties: StoreRoleLazyProperties[]): Promise<StoreRole> {
    const result = await this.apiService.getForAlgorithmApi<StoreRole>(algoStore, `/role/${id}`);

    const role = { ...result, users: [] };
    await getLazyProperties(result, role, lazyProperties, this.apiService, algoStore);

    return role;
  }

  async createRole(algoStore: AlgorithmStore, roleForm: StoreRoleForm): Promise<StoreRole> {
    const roleCreate: StoreRoleCreate = {
      ...roleForm
    };
    return await this.apiService.postForAlgorithmApi<StoreRole>(algoStore, `/role`, roleCreate);
  }

  async patchRole(algoStore: AlgorithmStore, role: StoreRole): Promise<StoreRole | null> {
    try {
      const requestBody: StoreRoleForm = {
        name: role.name,
        description: role.description,
        rules: role.rules.map((rule) => rule.id)
      };
      return await this.apiService.patchForAlgorithmApi<StoreRole>(algoStore, `/role/${role.id}`, requestBody);
    } catch {
      return null;
    }
  }

  async deleteRole(algoStore: AlgorithmStore, roleID: number): Promise<void> {
    await this.apiService.deleteForAlgorithmApi(algoStore, `/role/${roleID}?delete_dependents=true`);
  }
}
