import { TestBed } from '@angular/core/testing';

import { SocketioConnectService } from './socketio-connect.service';

describe('SocketioConnectService', () => {
  let service: SocketioConnectService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SocketioConnectService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
