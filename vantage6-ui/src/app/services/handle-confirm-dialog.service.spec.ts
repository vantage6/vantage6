import { TestBed } from '@angular/core/testing';

import { HandleConfirmDialogService } from './handle-confirm-dialog.service';

describe('HandleConfirmDialogService', () => {
  let service: HandleConfirmDialogService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(HandleConfirmDialogService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
