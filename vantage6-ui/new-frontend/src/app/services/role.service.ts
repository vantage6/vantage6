import { Injectable } from '@angular/core';
import { ApiService } from './api.service';

import { GetRoleParameters, Role } from '../models/api/role.model';
import { Pagination } from '../models/api/pagination.model';

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
}
