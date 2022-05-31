import { TestBed } from '@angular/core/testing';

import { RuleDataService } from './rule-data.service';

describe('RuleDataService', () => {
  let service: RuleDataService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RuleDataService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
