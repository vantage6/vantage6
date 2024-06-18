import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { StoreRole } from '../models/api/store-role.model';
import { Pagination } from '../models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class StoreRoleService {
  constructor(private apiService: ApiService) {}

  async getRoles(store_url: string): Promise<StoreRole[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<StoreRole>>(store_url, '/api/role', { per_page: 9999 });
    return result.data;
  }
}
