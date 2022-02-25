import { TestBed } from '@angular/core/testing';

import { ApiOrganizationService } from './organization.service';

describe('ApiOrganizationService', () => {
  let service: ApiOrganizationService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ApiOrganizationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
