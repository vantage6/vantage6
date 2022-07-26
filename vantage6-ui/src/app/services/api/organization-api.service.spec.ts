import { TestBed } from '@angular/core/testing';

import { OrganizationApiService } from './organization.service';

describe('OrganizationApiService', () => {
  let service: OrganizationApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(OrganizationApiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
