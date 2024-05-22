import { TestBed } from '@angular/core/testing';

import { StorePermissionService } from './store-permission.service';

describe('StorePermissionService', () => {
  let service: StorePermissionService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(StorePermissionService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
