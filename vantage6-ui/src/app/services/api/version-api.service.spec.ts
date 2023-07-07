import { TestBed } from '@angular/core/testing';

import { VersionApiService } from './version-api.service';

describe('VersionApiService', () => {
  let service: VersionApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(VersionApiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
