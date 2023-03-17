import { TestBed } from '@angular/core/testing';

import { RunApiService } from './run-api.service';

describe('RunApiService', () => {
  let service: RunApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RunApiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
