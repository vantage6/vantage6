import { TestBed } from '@angular/core/testing';

import { UserPermissionService } from './user-permission.service';

describe('UserPermissionService', () => {
  let service: UserPermissionService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(UserPermissionService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
