import { TestBed } from '@angular/core/testing';

import { RoleEditService } from './role-edit.service';

describe('RoleEditService', () => {
  let service: RoleEditService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RoleEditService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
