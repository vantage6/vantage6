import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { ResType } from 'src/app/shared/enum';
import { Rule } from 'src/app/interfaces/rule';

import { ApiService } from 'src/app/services/api/api.service';
import { ModalService } from 'src/app/services/common/modal.service';

@Injectable({
  providedIn: 'root',
})
export class ApiRuleService extends ApiService {
  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.RULE, http, modalService);
  }

  get_data(rule: Rule) {
    return {
      type: rule.type,
      operation: rule.operation,
      resource: rule.resource,
      scope: rule.scope,
    };
  }
}
