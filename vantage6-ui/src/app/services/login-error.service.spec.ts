import { TestBed } from '@angular/core/testing';

import { LoginErrorService } from './login-error.service';

describe('LoginErrorService', () => {
  let service: LoginErrorService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(LoginErrorService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
