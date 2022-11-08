import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { io, Socket } from 'socket.io-client';

import { environment } from 'src/environments/environment';
import { SnackbarService } from './snackbar.service';
import { TokenStorageService } from './token-storage.service';

@Injectable({
  providedIn: 'root',
})
export class SocketioService {
  public message$: BehaviorSubject<string> = new BehaviorSubject('');
  socket: Socket<any>;

  constructor(
    private tokenStorage: TokenStorageService,
    private snackbarService: SnackbarService
  ) {}

  setupConnection() {
    const token = this.tokenStorage.getToken();
    // connect to tasks namespace
    const namespace = '/tasks';
    this.socket = io(`${environment.server_url}${namespace}`, {
      extraHeaders: {
        Authorization: `Bearer ${token}`,
      },
    });
    this.subscribe();
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }

  subscribe() {
    // subscribe to various socket events
    // TODO I don't think we do anything with these messages? Delete?
    this.socket.on('message', (message: string) => {
      this.message$.next(message);
    });

    // give status messages when node comes online
    this.socket.on('node-online', (data: any) => {
      this.snackbarService.openNodeStatusSnackBar(
        `The node '${data.name}' just came online!`,
        data,
        true
      );
    });
    // ... and when a node goes offline
    this.socket.on('node-offline', (data: any) => {
      this.snackbarService.openNodeStatusSnackBar(
        `The node '${data.name}' just went offline!`,
        data,
        false
      );
    });
  }

  public sendMessage(message: string) {
    this.socket.emit('message', message);
  }

  public getMessages = () => {
    return this.message$.asObservable();
  };
}
