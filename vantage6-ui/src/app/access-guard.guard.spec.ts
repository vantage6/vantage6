import { TestBed } from '@angular/core/testing';

import { AccessGuardGuard } from './access-guard.guard';

describe('AccessGuardGuard', () => {
  let guard: AccessGuardGuard;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    guard = TestBed.inject(AccessGuardGuard);
  });

  it('should be created', () => {
    expect(guard).toBeTruthy();
  });
});
