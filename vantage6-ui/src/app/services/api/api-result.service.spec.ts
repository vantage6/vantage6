import { TestBed } from '@angular/core/testing';

import { ApiResultService } from './api-result.service';

describe('ApiResultService', () => {
  let service: ApiResultService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ApiResultService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
