import { TestBed } from '@angular/core/testing';

import { ApiTaskService } from './api-task.service';

describe('ApiTaskService', () => {
  let service: ApiTaskService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ApiTaskService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
