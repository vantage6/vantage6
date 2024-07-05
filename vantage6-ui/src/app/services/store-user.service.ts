import { Injectable } from '@angular/core';
import {
  StoreUser,
  StoreUserCreate,
  StoreUserFormSubmit,
  StoreUserLazyProperties,
  GetStoreUserParameters
} from '../models/api/store-user.model';
import { Pagination } from '../models/api/pagination.model';
import { ApiService } from './api.service';
import { getLazyProperties } from '../helpers/api.helper';

@Injectable({
  providedIn: 'root'
})
export class StoreUserService {
  constructor(private apiService: ApiService) {}

  async getPaginatedUsers(store_url: string, currentPage: number, parameters?: GetStoreUserParameters): Promise<Pagination<StoreUser>> {
    const result = await this.apiService.getForAlgorithmApiWithPagination<StoreUser>(store_url, `/api/user`, currentPage, {
      ...parameters
    });
    return result;
  }

  async getUser(store_url: string, id: string, lazyProperties: StoreUserLazyProperties[] = []): Promise<StoreUser> {
    const result = await this.apiService.getForAlgorithmApi<StoreUser>(store_url, `/api/user/${id}`);

    const user = { ...result, roles: [] };
    await getLazyProperties(result, user, lazyProperties, this.apiService, store_url);

    return user;
  }

  async createUser(store_url: string, user: StoreUserCreate): Promise<StoreUser> {
    return await this.apiService.postForAlgorithmApi<StoreUser>(store_url, `/api/user`, user);
  }

  async editUser(store_url: string, id: number, user: StoreUserFormSubmit): Promise<StoreUser> {
    return await this.apiService.patchForAlgorithmApi<StoreUser>(store_url, `/api/user/${id}`, user);
  }

  async deleteUser(store_url: string, id: number): Promise<void> {
    return await this.apiService.deleteForAlgorithmApi(store_url, `/api/user/${id}`);
  }
}
