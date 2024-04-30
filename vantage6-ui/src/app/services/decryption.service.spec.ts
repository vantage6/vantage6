import { TestBed } from '@angular/core/testing';

import { DecryptionService } from './decryption.service';

describe('DecryptionService', () => {
  let service: DecryptionService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(DecryptionService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
