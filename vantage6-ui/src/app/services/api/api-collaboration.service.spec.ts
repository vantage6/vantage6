import { TestBed } from '@angular/core/testing';

import { ApiCollaborationService } from './api-collaboration.service';

describe('ApiCollaborationService', () => {
  let service: ApiCollaborationService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ApiCollaborationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
