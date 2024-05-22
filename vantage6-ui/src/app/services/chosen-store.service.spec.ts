import { TestBed } from '@angular/core/testing';

import { ChosenStoreService } from './chosen-store.service';

describe('ChosenStoreService', () => {
  let service: ChosenStoreService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ChosenStoreService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
