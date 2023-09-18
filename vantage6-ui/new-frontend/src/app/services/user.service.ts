import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { BaseUser } from '../models/api/user.model';
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
}
