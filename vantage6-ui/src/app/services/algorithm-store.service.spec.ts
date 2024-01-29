import { TestBed } from '@angular/core/testing';

import { AlgorithmStoreService } from './algorithm-store.service';

describe('AlgorithmStoreService', () => {
  let service: AlgorithmStoreService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(AlgorithmStoreService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
