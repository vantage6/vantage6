import { TestBed } from '@angular/core/testing';

import { SignOutService } from './sign-out.service';

describe('SignOutService', () => {
  let service: SignOutService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SignOutService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
