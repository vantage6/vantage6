import { TestBed } from '@angular/core/testing';

import { NodeDataService } from './node-data.service';

describe('NodeDataService', () => {
  let service: NodeDataService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(NodeDataService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
