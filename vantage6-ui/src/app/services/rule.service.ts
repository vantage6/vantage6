import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { GetRuleParameters, Rule } from 'src/app/models/api/rule.model';
import { Pagination } from 'src/app/models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class RuleService {
  constructor(private apiService: ApiService) {}

  async getRules(parameters?: GetRuleParameters): Promise<Rule[]> {
    const result = await this.apiService.getForApi<Pagination<Rule>>('/rule', { ...parameters, no_pagination: 1 });
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
