import { TestBed } from '@angular/core/testing';

import { TaskApiService } from './api-task.service';

describe('TaskApiService', () => {
  let service: TaskApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TaskApiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
