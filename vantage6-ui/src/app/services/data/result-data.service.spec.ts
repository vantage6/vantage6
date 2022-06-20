import { TestBed } from '@angular/core/testing';

import { ResultDataService } from './result-data.service';

describe('ResultDataService', () => {
  let service: ResultDataService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ResultDataService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
