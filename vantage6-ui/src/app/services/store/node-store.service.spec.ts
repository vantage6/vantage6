import { TestBed } from '@angular/core/testing';

import { NodeEditService } from './node-edit.service';

describe('NodeEditService', () => {
  let service: NodeEditService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(NodeEditService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
