import { TestBed } from '@angular/core/testing';

import { ServerConfigService } from './server-config.service';

describe('ServerConfigService', () => {
  let service: ServerConfigService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ServerConfigService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
