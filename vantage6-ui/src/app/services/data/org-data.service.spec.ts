import { TestBed } from '@angular/core/testing';

import { OrgDataService } from './org-data.service';

describe('OrgDataService', () => {
  let service: OrgDataService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(OrgDataService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
