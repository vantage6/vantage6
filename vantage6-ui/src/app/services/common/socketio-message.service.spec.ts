import { TestBed } from '@angular/core/testing';

import { SocketioMessageService } from './socketio-message.service';

describe('SocketioMessageService', () => {
  let service: SocketioMessageService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SocketioMessageService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
