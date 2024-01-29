import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { GetRuleParameters, Rule } from '../models/api/rule.model';
import { Pagination } from '../models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class RuleService {
  constructor(private apiService: ApiService) {}

  async getAllRules(roleId?: string): Promise<Rule[]> {
    const params: GetRuleParameters = { no_pagination: 1 };
    if (roleId) params.role_id = roleId;
    return this.getRules(params);
  }

  async getRules(parameters?: GetRuleParameters): Promise<Rule[]> {
    //TODO: Add backend no pagination instead of page size 9999
    const result = await this.apiService.getForApi<Pagination<Rule>>('/rule', { ...parameters });
    return result.data;
  }

  async getRulesOfRoles(roleIds: number[]): Promise<Rule[]> {
    let roleRules: Rule[] = [];
    const promises = roleIds.map(async (id) => {
      const rules = await this.getRules({ role_id: id.toString(), no_pagination: 1 });
      roleRules = roleRules.concat(rules);
    });
    await Promise.all(promises);
    return roleRules;
  }
}
