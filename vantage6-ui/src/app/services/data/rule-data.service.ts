import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Rule } from 'src/app/interfaces/rule';
import { ApiRuleService } from 'src/app/services//api/api-rule.service';
import { ConvertJsonService } from 'src/app/services//common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { Resource } from 'src/app/shared/types';

@Injectable({
  providedIn: 'root',
})
export class RuleDataService extends BaseDataService {
  constructor(
    protected apiService: ApiRuleService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
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
}
