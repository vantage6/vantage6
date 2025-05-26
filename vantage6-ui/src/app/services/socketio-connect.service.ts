import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { io, Socket } from 'socket.io-client';

import { environment } from 'src/environments/environment';
import { AlgorithmLogMsg, AlgorithmStatusChangeMsg, NewTaskMsg, NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class SocketioConnectService {
  nodeStatusUpdate$: BehaviorSubject<NodeOnlineStatusMsg | null> = new BehaviorSubject<NodeOnlineStatusMsg | null>(null);
  algoStatusUpdate$: BehaviorSubject<AlgorithmStatusChangeMsg | null> = new BehaviorSubject<AlgorithmStatusChangeMsg | null>(null);
  taskCreated$: BehaviorSubject<NewTaskMsg | null> = new BehaviorSubject<NewTaskMsg | null>(null);
  algoLogUpdate$: BehaviorSubject<AlgorithmLogMsg | null> = new BehaviorSubject<AlgorithmLogMsg | null>(null);
  socket: Socket | null = null;

  constructor(private authService: AuthService) {}

  connect() {
    if (this.socket === null) {
      // TODO get token
      const token = this.authService.getToken();
      // connect to tasks namespace
      const namespace = '/tasks';
      this.socket = io(`${environment.server_url}${namespace}`, {
        withCredentials: true,
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
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    this.socket?.on('node-online', (data: any) => {
      this.nodeStatusUpdate$.next({
        id: data.id,
        name: data.name,
        online: true
      });
    });
    // ... and when a node goes offline
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    this.socket?.on('node-offline', (data: any) => {
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
    this.socket?.on('new_task_update', (data) => {
      this.taskCreated$.next(data);
    });

    // get log messages from algorithm
    this.socket?.on('algorithm_log', (data: AlgorithmLogMsg) => {
      this.algoLogUpdate$.next(data);
    });
  }

  public getNodeStatusUpdates() {
    return this.nodeStatusUpdate$.asObservable();
  }

  public getAlgorithmStatusUpdates() {
    return this.algoStatusUpdate$.asObservable();
  }

  public getNewTaskUpdates() {
    return this.taskCreated$.asObservable();
  }

  public getAlgorithmLogUpdates() {
    return this.algoLogUpdate$.asObservable();
  }
}
