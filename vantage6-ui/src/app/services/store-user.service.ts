import { Injectable } from '@angular/core';
import { StoreUser, getStoreUserParameters } from '../models/api/store-user.model';
import { Pagination } from '../models/api/pagination.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class StoreUserService {
  constructor(private apiService: ApiService) {}

  async getPaginatedUsers(store_url: string, currentPage: number, parameters?: getStoreUserParameters): Promise<Pagination<StoreUser>> {
    const result = await this.apiService.getForAlgorithmApiWithPagination<StoreUser>(store_url, `/api/user`, currentPage, {
      ...parameters
    });
    return result;
  }
}
