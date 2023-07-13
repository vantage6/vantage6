import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Rule, RuleGroup } from 'src/app/interfaces/rule';
import { Pagination, allPages } from 'src/app/interfaces/utils';
import { RuleApiService } from 'src/app/services//api/rule-api.service';
import { ConvertJsonService } from 'src/app/services//common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { OpsType, ResType, ScopeType } from 'src/app/shared/enum';
import { deepcopy } from 'src/app/shared/utils';

/**
 * Service for retrieving and updating rule data.
 */
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
    /**
     * Get all rules. If the rules are not in the cache, they will be requested
     * from the vantage6 server.
     *
     * @param pagination The pagination parameters to use.
     * @param force_refresh Whether to force a refresh of the cache.
     * @param user_id The id of the user to get the rules for. If null, get all
     * rules.
     * @returns An observable of the rules.
     */
    // TODO instead of having user_id as a parameter, those rules should be
    // obtained through the list_with_params function
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
  ): Promise<Observable<Rule[]>> {
    /**
     * Get rules with the given parameters. If the rules are not in the cache,
     * they will be requested from the vantage6 server.
     *
     * @param pagination The pagination parameters to use.
     * @param request_params The parameters to use in the request.
     * @returns An observable of the rules.
     */
    if (pagination.all_pages === true) {
      request_params = { ...request_params, no_pagination: 1 };
    }
    return (await super.list_with_params_base(
      this.convertJsonService.getRule,
      request_params,
      pagination
    )).asObservable() as Observable<Rule[]>;
  }

  async ruleGroups(): Promise<Observable<RuleGroup[]>> {
    /**
     * Get the rules and then divide them in groups, based on resource, scope
     * and operation.
     *
     * @returns An observable of the rule groups.
     */
    if (this.rule_groups.value.length > 0) {
      return this.rule_groups.asObservable();
    }

    // set list of all rules
    await this.list();

    this.setRuleGroups();

    return this.rule_groups.asObservable();
  }

  private setRuleGroups(): void {
    /**
     * Divide the rules in groups, based on resource, scope and operation.
     */
    // sort rules by resource, then scope, then operation
    this.resource_list.next(
      this.sortRules(this.resource_list.value as Rule[]) as Rule[]
    );

    // divide sorted rules in groups
    let rule_groups = this.makeRuleGroups();
    this.rule_groups.next(rule_groups);
  }

  private sortRules(rules: Rule[]): Rule[] {
    /**
     * Sort rules by resource, then scope, then operation.
     *
     * @param rules The rules to sort.
     * @returns The sorted rules.
     */
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

  private makeRuleGroups(): RuleGroup[] {
    /**
     * Create the rule groups from the sorted rules.
     *
     * @returns The rule groups.
     */
    let rule_groups: RuleGroup[] = [];
    let current_rule_group: RuleGroup | undefined = undefined;
    for (let rule of this.resource_list.value as Rule[]) {
      if (current_rule_group === undefined) {
        // first rule: make new rule group
        current_rule_group = this.newRuleGroup(rule);
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
        current_rule_group = this.newRuleGroup(rule);
      }
    }
    // add last rule group
    if (current_rule_group !== undefined) {
      rule_groups.push(deepcopy(current_rule_group));
    }
    return rule_groups;
  }

  private newRuleGroup(rule: Rule): RuleGroup {
    /**
     * Create a new rule group with the given rule.
     */
    return {
      resource: rule.resource,
      scope: rule.scope,
      rules: [rule],
    };
  }
}
