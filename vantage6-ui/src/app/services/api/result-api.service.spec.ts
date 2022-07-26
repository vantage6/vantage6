import { TestBed } from '@angular/core/testing';

import { ResultApiService } from './result-api.service';

describe('ResultApiService', () => {
  let service: ResultApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ResultApiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
