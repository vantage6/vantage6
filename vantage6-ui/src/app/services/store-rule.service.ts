import { Injectable } from '@angular/core';
import { GetStoreRuleParameters, StoreRule } from 'src/app/models/api/rule.model';
import { Pagination } from 'src/app/models/api/pagination.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class StoreRuleService {
  constructor(private apiService: ApiService) {}

  async getRules(store_url: string, parameters?: GetStoreRuleParameters, showAuthError: boolean = true): Promise<StoreRule[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<StoreRule>>(
      `${store_url}/api`,
      '/rule',
      {
        ...parameters,
        no_pagination: 1
      },
      showAuthError
    );
    return result.data;
  }

  async getRulesForRoles(store_url: string, roleIds: number[]): Promise<StoreRule[]> {
    let roleRules: StoreRule[] = [];
    const promises = roleIds.map(async (id) => {
      const rules = await this.getRules(store_url, { role_id: id.toString(), no_pagination: 1 });
      roleRules = roleRules.concat(rules);
    });
    await Promise.all(promises);
    return roleRules;
  }
}
