import { TestBed } from '@angular/core/testing';

import { ApiRuleService } from './api-rule.service';

describe('ApiRuleService', () => {
  let service: ApiRuleService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ApiRuleService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
