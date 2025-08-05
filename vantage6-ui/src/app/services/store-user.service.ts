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
import { AlgorithmStore } from '../models/api/algorithmStore.model';

@Injectable({
  providedIn: 'root'
})
export class StoreUserService {
  constructor(private apiService: ApiService) {}

  async getUsers(algoStore: AlgorithmStore, parameters?: GetStoreUserParameters): Promise<StoreUser[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<StoreUser>>(algoStore, `/user`, {
      per_page: 9999,
      ...parameters
    });
    return result.data;
  }

  async getPaginatedUsers(
    algoStore: AlgorithmStore,
    currentPage: number,
    parameters?: GetStoreUserParameters
  ): Promise<Pagination<StoreUser>> {
    const result = await this.apiService.getForAlgorithmApiWithPagination<StoreUser>(algoStore, `/user`, currentPage, {
      ...parameters
    });
    return result;
  }

  async getUser(algoStore: AlgorithmStore, id: string, lazyProperties: StoreUserLazyProperties[] = []): Promise<StoreUser> {
    const result = await this.apiService.getForAlgorithmApi<StoreUser>(algoStore, `/user/${id}`);

    const user = { ...result, roles: [] };
    await getLazyProperties(result, user, lazyProperties, this.apiService, algoStore);

    return user;
  }

  async createUser(algoStore: AlgorithmStore, user: StoreUserCreate): Promise<StoreUser> {
    return await this.apiService.postForAlgorithmApi<StoreUser>(algoStore, `/user`, user);
  }

  async editUser(algoStore: AlgorithmStore, id: number, user: StoreUserFormSubmit): Promise<StoreUser> {
    return await this.apiService.patchForAlgorithmApi<StoreUser>(algoStore, `/user/${id}`, user);
  }

  async deleteUser(algoStore: AlgorithmStore, id: number): Promise<void> {
    return await this.apiService.deleteForAlgorithmApi(algoStore, `/user/${id}`);
  }
}
