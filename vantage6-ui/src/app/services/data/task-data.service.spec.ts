import { TestBed } from '@angular/core/testing';

import { TaskDataService } from './task-data.service';

describe('TaskDataService', () => {
  let service: TaskDataService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TaskDataService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
