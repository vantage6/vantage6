import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { GetRuleParameters, Rule } from '../models/api/rule.model';
import { Pagination } from '../models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class RuleService {
  constructor(private apiService: ApiService) {}

  async getAllRules(): Promise<Rule[]> {
    return this.getRules({ no_pagination: 1 });
  }

  async getRules(parameters?: GetRuleParameters): Promise<Rule[]> {
    //TODO: Add backend no pagination instead of page size 9999
    const result = await this.apiService.getForApi<Pagination<Rule>>('/rule', { ...parameters });
    return result.data;
  }
}
