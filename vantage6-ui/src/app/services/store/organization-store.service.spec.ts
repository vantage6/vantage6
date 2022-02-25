import { TestBed } from '@angular/core/testing';

import { OrganizationStoreService } from './organization-store.service';

describe('OrganizationStoreService', () => {
  let service: OrganizationStoreService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(OrganizationStoreService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
