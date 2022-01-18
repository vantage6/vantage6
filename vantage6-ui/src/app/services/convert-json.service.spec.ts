import { TestBed } from '@angular/core/testing';

import { ConvertJsonService } from './convert-json.service';

describe('ConvertJsonService', () => {
  let service: ConvertJsonService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ConvertJsonService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
