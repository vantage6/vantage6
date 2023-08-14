import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { environment } from 'src/environments/environment';
import { Pagination } from '../models/api/pagination.model';
import { BaseOrganization } from '../models/api/organization.model';

@Injectable({
  providedIn: 'root'
})
export class OrganizationService {
  constructor(private apiService: ApiService) {}

  async getOrganizations(): Promise<BaseOrganization[]> {
    const result = await this.apiService.getForApi<Pagination<BaseOrganization>>('/organization');
    return result.data;
  }
}
