import { TestBed } from '@angular/core/testing';

import { StoreRuleService } from './store-rule.service';

describe('StoreRuleService', () => {
  let service: StoreRuleService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(StoreRuleService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
