import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Rule, RuleGroup } from 'src/app/interfaces/rule';
import { ApiRuleService } from 'src/app/services//api/api-rule.service';
import { ConvertJsonService } from 'src/app/services//common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { OpsType, ResType, ScopeType } from 'src/app/shared/enum';
import { Resource } from 'src/app/shared/types';
import { deepcopy } from 'src/app/shared/utils';
import { TokenStorageService } from '../common/token-storage.service';

@Injectable({
  providedIn: 'root',
})
export class RuleDataService extends BaseDataService {
  is_logged_in = false;
  all_rules: Rule[] = [];
  all_rules_bhs = new BehaviorSubject<Rule[]>([]);
  rule_groups: RuleGroup[] = [];
  rule_groups_bhs = new BehaviorSubject<RuleGroup[]>([]);

  constructor(
    protected apiService: ApiRuleService,
    protected convertJsonService: ConvertJsonService,
    private tokenStorageService: TokenStorageService
  ) {
    super(apiService, convertJsonService);
    this.tokenStorageService.isLoggedIn().subscribe((is_logged_in) => {
      this.is_logged_in = is_logged_in;
    });
  }

  async list(
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Observable<Rule[]>> {
    return (await super.list(
      convertJsonFunc,
      additionalConvertArgs,
      force_refresh
    )) as Observable<Rule[]>;
  }

  getRules(): Observable<Rule[]> {
    return this.all_rules_bhs.asObservable();
  }

  getRuleGroups(): Observable<RuleGroup[]> {
    return this.rule_groups_bhs.asObservable();
  }

  getRuleGroupsCopy(): RuleGroup[] {
    return JSON.parse(JSON.stringify(this.rule_groups));
  }

  async getAllRules(): Promise<Rule[]> {
    // if rules are not set, set them (and wait). If already set, return them.
    if (this.all_rules.length === 0) {
      await this.setAllRules();
      this.all_rules_bhs.next(this.all_rules);
    }
    return this.all_rules;
  }

  async setAllRules(): Promise<void> {
    if (this.all_rules.length > 0 || !this.is_logged_in) return;

    // set list of all rules
    await this.list(this.convertJsonService.getRule);

    await this._setAllRules();
    this._setRuleGroups();
  }

  private async _setAllRules(): Promise<void> {
    this.all_rules = [];
    for (let rule of this.resource_list.value) {
      this.all_rules.push(rule as Rule);
    }
  }

  _setRuleGroups(): void {
    // sort rules by resource, then scope, then operation
    this.all_rules = this._sortRules(this.all_rules);

    // divide sorted rules in groups
    this.rule_groups = this._makeRuleGroups();
    this.rule_groups_bhs.next(this.rule_groups);
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
    for (let rule of this.all_rules) {
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
