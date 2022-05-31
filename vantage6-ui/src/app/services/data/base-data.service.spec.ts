import { TestBed } from '@angular/core/testing';

import { BaseDataService } from './base-data.service';

describe('BaseDataService', () => {
  let service: BaseDataService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(BaseDataService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
