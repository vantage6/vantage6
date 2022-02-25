import { TestBed } from '@angular/core/testing';

import { NodeStoreService } from './node-store.service';

describe('NodeStoreService', () => {
  let service: NodeStoreService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(NodeStoreService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
