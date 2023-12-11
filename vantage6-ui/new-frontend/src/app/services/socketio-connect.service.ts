import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { io, Socket } from 'socket.io-client';

import { environment } from 'src/environments/environment';
import { TokenStorageService } from './token-storage.service';
import { AlgorithmStatusChangeMsg, NewTaskMsg, NodeOnlineStatusMsg } from '../models/socket-messages.model';

@Injectable({
  providedIn: 'root'
})
export class SocketioConnectService {
  nodeStatusUpdate$: BehaviorSubject<NodeOnlineStatusMsg | null> = new BehaviorSubject<NodeOnlineStatusMsg | null>(null);
  algoStatusUpdate$: BehaviorSubject<AlgorithmStatusChangeMsg | null> = new BehaviorSubject<AlgorithmStatusChangeMsg | null>(null);
  taskCreated$: BehaviorSubject<NewTaskMsg | null> = new BehaviorSubject<NewTaskMsg | null>(null);
  socket: Socket | null = null;

  constructor(private tokenStorageService: TokenStorageService) {}

  connect() {
    if (this.socket === null) {
      const token = this.tokenStorageService.getToken();
      // connect to tasks namespace
      const namespace = '/tasks';
      this.socket = io(`${environment.server_url}${namespace}`, {
        extraHeaders: {
          Authorization: `Bearer ${token}`
        }
      });
      this.subscribe();
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }

  subscribe() {
    // subscribe to various socket events

    // update observable (generate status messages downstream) when node comes
    //online
    this.socket?.on('node-online', (data) => {
      this.nodeStatusUpdate$.next({
        id: data.id,
        name: data.name,
        online: true
      });
    });
    // ... and when a node goes offline
    this.socket?.on('node-offline', (data) => {
      this.nodeStatusUpdate$.next({
        id: data.id,
        name: data.name,
        online: false
      });
    });

    // get messages when algorithm changes status
    this.socket?.on('algorithm_status_change', (data) => {
      this.algoStatusUpdate$.next(data);
    });

    // get messages when a new task is created
    this.socket?.on('new_task', (data) => {
      this.taskCreated$.next(data);
    });
  }

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
