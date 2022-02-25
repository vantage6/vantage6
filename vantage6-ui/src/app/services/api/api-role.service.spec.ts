import { TestBed } from '@angular/core/testing';

import { ApiRoleService } from './api-role.service';

describe('ApiRoleService', () => {
  let service: ApiRoleService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ApiRoleService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
