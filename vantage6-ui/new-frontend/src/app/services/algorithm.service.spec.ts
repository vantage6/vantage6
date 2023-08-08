import { TestBed } from '@angular/core/testing';

import { AlgorithmService } from './algorithm.service';

describe('AlgorithmService', () => {
  let service: AlgorithmService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(AlgorithmService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
