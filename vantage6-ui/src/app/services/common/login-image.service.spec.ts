import { TestBed } from '@angular/core/testing';

import { LoginImageService } from './login-image.service';

describe('LoginImageService', () => {
  let service: LoginImageService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(LoginImageService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
