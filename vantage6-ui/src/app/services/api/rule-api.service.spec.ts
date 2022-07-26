import { TestBed } from '@angular/core/testing';

import { RuleApiService } from './rule-api.service';

describe('RuleApiService', () => {
  let service: RuleApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RuleApiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
