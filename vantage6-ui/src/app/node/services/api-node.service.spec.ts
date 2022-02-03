import { TestBed } from '@angular/core/testing';

import { ApiNodeService } from './api-node.service';

describe('ApiNodeService', () => {
  let service: ApiNodeService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ApiNodeService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
