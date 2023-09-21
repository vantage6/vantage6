import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { ResType } from 'src/app/shared/enum';
import { Rule } from 'src/app/interfaces/rule';

import { BaseApiService } from 'src/app/services/api/base-api.service';
import { ModalService } from 'src/app/services/common/modal.service';

/**
 * Service for interacting with the rule endpoints of the API
 */
@Injectable({
  providedIn: 'root',
})
export class RuleApiService extends BaseApiService {
  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.RULE, http, modalService);
  }

  /**
   * Implement the abstract get_data function of the base class. This is not
   * useful for rules, since they are not updated via the API.
   */
  get_data(rule: Rule) {
    // raise error if this function is called
    throw new Error('Rules cannot be updated via the API');
  }
}
