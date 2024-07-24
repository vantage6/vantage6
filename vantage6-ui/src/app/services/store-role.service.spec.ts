import { TestBed } from '@angular/core/testing';

import { StoreRoleService } from './store-role.service';

describe('StoreRoleService', () => {
  let service: StoreRoleService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(StoreRoleService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
