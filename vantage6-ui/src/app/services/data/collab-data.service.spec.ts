import { TestBed } from '@angular/core/testing';

import { CollabDataService } from './collab-data.service';

describe('CollabDataService', () => {
  let service: CollabDataService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(CollabDataService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
