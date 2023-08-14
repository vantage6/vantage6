import { TestBed } from '@angular/core/testing';

import { CollaborationService } from './collaboration.service';

describe('CollaborationService', () => {
  let service: CollaborationService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(CollaborationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
