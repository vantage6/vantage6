import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { io, Socket } from 'socket.io-client';

import { environment } from 'src/environments/environment';
import { TokenStorageService } from './token-storage.service';

@Injectable({
  providedIn: 'root',
})
export class SocketioConnectService {
  public message$: BehaviorSubject<string> = new BehaviorSubject('');
  public nodeStatusUpdate$: BehaviorSubject<any> = new BehaviorSubject({});
  public algoStatusUpdate$: BehaviorSubject<any> = new BehaviorSubject({});
  public taskCreated$: BehaviorSubject<any> = new BehaviorSubject({});
  socket: Socket<any>;

  constructor(private tokenStorage: TokenStorageService) {}

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

    // update observable (generate status messages downstream) when node comes
    //online
    this.socket.on('node-online', (data: any) => {
      this.nodeStatusUpdate$.next({
        id: data.id,
        name: data.name,
        online: true,
      });
    });
    // ... and when a node goes offline
    this.socket.on('node-offline', (data: any) => {
      this.nodeStatusUpdate$.next({
        id: data.id,
        name: data.name,
        online: false,
      });
    });

    // get messages when algorithm changes status
    this.socket.on('algorithm_status_change', (data: any) => {
      this.algoStatusUpdate$.next(data);
    });
    this.socket.on('task_created', (data: any) => {
      this.taskCreated$.next(data);
    });
  }

  public getMessages = () => {
    return this.message$.asObservable();
  };

  public getNodeStatusUpdates() {
    return this.nodeStatusUpdate$.asObservable();
  }

  public getAlgorithmStatusUpdates() {
    return this.algoStatusUpdate$.asObservable();
  }
  public getTaskCreatedUpdates() {
    return this.taskCreated$.asObservable();
  }
}
