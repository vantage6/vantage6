import { TestBed } from '@angular/core/testing';

import { CollabApiService } from './collaboration-api.service';

describe('CollabApiService', () => {
  let service: CollabApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(CollabApiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
