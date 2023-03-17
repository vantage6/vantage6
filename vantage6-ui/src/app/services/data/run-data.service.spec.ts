import { TestBed } from '@angular/core/testing';

import { RunDataService } from './run-data.service';

describe('RunDataService', () => {
  let service: RunDataService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RunDataService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
