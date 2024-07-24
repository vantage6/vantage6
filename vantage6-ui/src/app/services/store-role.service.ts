import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { GetStoreRoleParameters, StoreRole, StoreRoleLazyProperties } from '../models/api/store-role.model';
import { Pagination } from '../models/api/pagination.model';
import { getLazyProperties } from '../helpers/api.helper';

@Injectable({
  providedIn: 'root'
})
export class StoreRoleService {
  constructor(private apiService: ApiService) {}

  async getRoles(store_url: string): Promise<StoreRole[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<StoreRole>>(store_url, '/api/role', { per_page: 9999 });
    return result.data;
  }

  async getPaginatedRoles(store_url: string, currentPage: number, parameters?: GetStoreRoleParameters): Promise<Pagination<StoreRole>> {
    const result = await this.apiService.getForAlgorithmApiWithPagination<StoreRole>(store_url, `/api/role`, currentPage, {
      ...parameters
    });
    return result;
  }

  async getRole(store_url: string, id: string, lazyProperties: StoreRoleLazyProperties[]): Promise<StoreRole> {
    const result = await this.apiService.getForAlgorithmApi<StoreRole>(store_url, `/api/role/${id}`);

    const role = { ...result, users: [] };
    await getLazyProperties(result, role, lazyProperties, this.apiService, store_url);

    return role;
  }
}
