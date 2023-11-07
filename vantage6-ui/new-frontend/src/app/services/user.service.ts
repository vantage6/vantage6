import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { BaseUser, GetUserParameters, User, UserCreate, UserEdit, UserLazyProperties } from '../models/api/user.model';
import { Pagination } from '../models/api/pagination.model';
import { getLazyProperties } from '../helpers/api.helper';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  constructor(private apiService: ApiService) {}

  async getPaginatedUsers(currentPage: number, parameters?: GetUserParameters): Promise<Pagination<BaseUser>> {
    const result = await this.apiService.getForApiWithPagination<BaseUser>(`/user`, currentPage, { ...parameters });
    return result;
  }

  async getUser(id: string, lazyProperties: UserLazyProperties[] = []): Promise<User> {
    const result = await this.apiService.getForApi<BaseUser>(`/user/${id}`);

    const user: User = { ...result, organization: undefined, roles: [] };
    await getLazyProperties(result, user, lazyProperties, this.apiService);

    return user;
  }

  async createUser(user: UserCreate): Promise<BaseUser> {
    return await this.apiService.postForApi<BaseUser>(`/user`, user);
  }

  async editUser(userID: string, user: UserEdit): Promise<BaseUser> {
    return await this.apiService.patchForApi<BaseUser>(`/user/${userID}`, user);
  }

  async deleteUser(id: number): Promise<void> {
    return await this.apiService.deleteForApi(`/user/${id}`);
  }
}
