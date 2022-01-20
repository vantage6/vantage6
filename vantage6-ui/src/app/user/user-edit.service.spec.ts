import { TestBed } from '@angular/core/testing';

import { UserEditService } from './user-edit.service';

describe('UserEditService', () => {
  let service: UserEditService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(UserEditService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
