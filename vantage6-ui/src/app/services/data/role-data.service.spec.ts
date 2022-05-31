import { TestBed } from '@angular/core/testing';

import { RoleDataService } from './role-data.service';

describe('RoleDataService', () => {
  let service: RoleDataService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RoleDataService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
