import { TestBed } from '@angular/core/testing';

import { StoreReviewService } from './store-review.service';

describe('StoreReviewService', () => {
  let service: StoreReviewService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(StoreReviewService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
