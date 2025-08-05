import { Injectable } from '@angular/core';
import { GetStoreRuleParameters, StoreRule } from 'src/app/models/api/rule.model';
import { Pagination } from 'src/app/models/api/pagination.model';
import { ApiService } from './api.service';
import { AlgorithmStore } from '../models/api/algorithmStore.model';

@Injectable({
  providedIn: 'root'
})
export class StoreRuleService {
  constructor(private apiService: ApiService) {}

  async getRules(algoStore: AlgorithmStore, parameters?: GetStoreRuleParameters, showAuthError: boolean = true): Promise<StoreRule[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<StoreRule>>(
      algoStore,
      '/rule',
      {
        ...parameters,
        no_pagination: 1
      },
      showAuthError
    );
    return result.data;
  }

  async getRulesForRoles(algoStore: AlgorithmStore, roleIds: number[]): Promise<StoreRule[]> {
    let roleRules: StoreRule[] = [];
    const promises = roleIds.map(async (id) => {
      const rules = await this.getRules(algoStore, { role_id: id.toString(), no_pagination: 1 });
      roleRules = roleRules.concat(rules);
    });
    await Promise.all(promises);
    return roleRules;
  }
}
