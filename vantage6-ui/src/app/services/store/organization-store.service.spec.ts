import { TestBed } from '@angular/core/testing';

import { OrganizationEditService } from './organization-edit.service';

describe('OrganizationEditService', () => {
  let service: OrganizationEditService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(OrganizationEditService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
