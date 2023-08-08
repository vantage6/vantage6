import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { environment } from 'src/environments/environment';
import { Pagination } from '../models/api/pagination.model';
import { Organization } from '../models/api/organization.model';

@Injectable({
  providedIn: 'root'
})
export class OrganizationService {
  constructor(private apiService: ApiService) {}

  async getOrganizations(): Promise<Organization[]> {
    const result = await this.apiService.get<Pagination<Organization>>(environment.api_url + '/organization');
    return result.data;
  }
}
