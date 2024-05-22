import { Injectable } from '@angular/core';
import { GetStoreRuleParameters, StoreRule } from '../models/api/rule.model';
import { Pagination } from '../models/api/pagination.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class StoreRuleService {
  constructor(private apiService: ApiService) {}

  async getRules(store_url: string, parameters?: GetStoreRuleParameters): Promise<StoreRule[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<StoreRule>>(`${store_url}/api`, '/rule', {
      ...parameters,
      no_pagination: 1
    });
    return result.data;
  }
}
