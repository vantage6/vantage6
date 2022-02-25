import { TestBed } from '@angular/core/testing';

import { RoleStoreService } from './role-store.service';

describe('RoleStoreService', () => {
  let service: RoleStoreService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RoleStoreService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
