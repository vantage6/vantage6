import { TestBed } from '@angular/core/testing';

import { StoreBaseService } from './store-base.service';

describe('StoreBaseService', () => {
  let service: StoreBaseService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(StoreBaseService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
