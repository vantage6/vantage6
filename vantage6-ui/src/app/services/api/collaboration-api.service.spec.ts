import { TestBed } from '@angular/core/testing';

import { CollabApiService } from './api-collaboration.service';

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
