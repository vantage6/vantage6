import { TestBed } from '@angular/core/testing';

import { ChosenCollaborationService } from './chosen-collaboration.service';

describe('ChosenCollaborationService', () => {
  let service: ChosenCollaborationService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ChosenCollaborationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
