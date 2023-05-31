import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Rule, RuleGroup } from 'src/app/interfaces/rule';
import { Pagination, allPages } from 'src/app/interfaces/utils';
import { RuleApiService } from 'src/app/services//api/rule-api.service';
import { ConvertJsonService } from 'src/app/services//common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { OpsType, ResType, ScopeType } from 'src/app/shared/enum';
import { deepcopy } from 'src/app/shared/utils';

@Injectable({
  providedIn: 'root',
})
export class RuleDataService extends BaseDataService {
  rule_groups = new BehaviorSubject<RuleGroup[]>([]);

  constructor(
    protected apiService: RuleApiService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async list(
    pagination: Pagination = allPages(),
    force_refresh: boolean = false,
    user_id: number | null = null
  ): Promise<Observable<Rule[]>> {
    // only get rules for specific user if requested
    let params: any = user_id === null ? {} : { user_id: user_id };
    if (pagination.all_pages === true) {
      params = { ...params, no_pagination: 1 };
    }
    // get rules
    return (await super.list_base(
      this.convertJsonService.getRule,
      pagination,
      force_refresh,
      params
    )).asObservable() as Observable<Rule[]>;
  }

  async list_with_params(
    pagination: Pagination = allPages(),
    request_params: any = {}
  ): Promise<Rule[]> {
    if (pagination.all_pages === true) {
      request_params = { ...request_params, no_pagination: 1 };
    }
    return (await super.list_with_params_base(
      this.convertJsonService.getRule,
      request_params,
      pagination
    )) as Rule[];
  }

  async ruleGroups(): Promise<Observable<RuleGroup[]>> {
    if (this.rule_groups.value.length > 0) {
      return this.rule_groups.asObservable();
    }

    // set list of all rules
    await this.list();

    this._setRuleGroups();

    return this.rule_groups.asObservable();
  }

  _setRuleGroups(): void {
    // sort rules by resource, then scope, then operation
    this.resource_list.next(
      this._sortRules(this.resource_list.value as Rule[]) as Rule[]
    );

    // divide sorted rules in groups
    let rule_groups = this._makeRuleGroups();
    this.rule_groups.next(rule_groups);
  }

  _sortRules(rules: Rule[]): Rule[] {
    const resource_order = Object.values(ResType);
    const scope_order = Object.values(ScopeType);
    const operation_order = Object.values(OpsType);
    return rules.sort((a, b) => {
      if (a.resource !== b.resource) {
        return (
          resource_order.indexOf(a.resource) -
          resource_order.indexOf(b.resource)
        );
      } else if (a.scope !== b.scope) {
        return scope_order.indexOf(a.scope) - scope_order.indexOf(b.scope);
      } else {
        return (
          operation_order.indexOf(a.operation) -
          operation_order.indexOf(b.operation)
        );
      }
    });
  }

  _makeRuleGroups(): RuleGroup[] {
    let rule_groups: RuleGroup[] = [];
    let current_rule_group: RuleGroup | undefined = undefined;
    for (let rule of this.resource_list.value as Rule[]) {
      if (current_rule_group === undefined) {
        // first rule: make new rule group
        current_rule_group = this._newRuleGroup(rule);
      } else if (
        current_rule_group.resource === rule.resource &&
        current_rule_group.scope === rule.scope
      ) {
        // the rule is in the same group as previous rule
        current_rule_group.rules.push(rule);
      } else {
        // New Rule group!
        // First, save the previous rule group
        rule_groups.push(deepcopy(current_rule_group));

        // start new rule group
        current_rule_group = this._newRuleGroup(rule);
      }
    }
    // add last rule group
    if (current_rule_group !== undefined) {
      rule_groups.push(deepcopy(current_rule_group));
    }
    return rule_groups;
  }

  _newRuleGroup(rule: Rule): RuleGroup {
    return {
      resource: rule.resource,
      scope: rule.scope,
      rules: [rule],
    };
  }
}
