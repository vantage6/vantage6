import { TestBed } from '@angular/core/testing';

import { ApiUserService } from './api-user.service';

describe('ApiUserService', () => {
  let service: ApiUserService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ApiUserService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
