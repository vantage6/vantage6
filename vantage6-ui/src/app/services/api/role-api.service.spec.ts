import { TestBed } from '@angular/core/testing';

import { RoleApiService } from './role-api.service';

describe('RoleApiService', () => {
  let service: RoleApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RoleApiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
