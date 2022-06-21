import { TestBed } from '@angular/core/testing';

import { DownloadFileService } from './download-file.service';

describe('DownloadFileService', () => {
  let service: DownloadFileService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(DownloadFileService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
