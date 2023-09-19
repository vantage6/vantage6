import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { BaseUser, User, UserLazyProperties } from '../models/api/user.model';
import { Pagination } from '../models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  constructor(private apiService: ApiService) {}

  async getPaginatedUsers(currentPage: number): Promise<Pagination<BaseUser>> {
    const result = await this.apiService.getForApiWithPagination<BaseUser>(`/user`, currentPage);
    return result;
  }

  async getUser(id: string, lazyProperties: UserLazyProperties[] = []): Promise<User> {
    const result = await this.apiService.getForApi<BaseUser>(`/user/${id}`);

    const user: User = { ...result, organization: undefined, roles: [] };
    await Promise.all(
      (lazyProperties as string[]).map(async (lazyProperty) => {
        if (!(result as any)[lazyProperty]) return;

        if ((result as any)[lazyProperty].hasOwnProperty('link') && (result as any)[lazyProperty].link) {
          const resultProperty = await this.apiService.getForApi<any>((result as any)[lazyProperty].link);
          (user as any)[lazyProperty] = resultProperty;
        } else {
          const resultProperty = await this.apiService.getForApi<Pagination<any>>((result as any)[lazyProperty] as string);
          (user as any)[lazyProperty] = resultProperty.data;
        }
      })
    );

    return user;
  }

  async delete(id: number): Promise<void> {
    return await this.apiService.deleteForApi(`/user/${id}`);
  }
}
