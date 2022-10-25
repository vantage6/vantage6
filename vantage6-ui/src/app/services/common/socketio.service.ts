import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { io, Socket } from 'socket.io-client';

import { environment } from 'src/environments/environment';
import { TokenStorageService } from './token-storage.service';

@Injectable({
  providedIn: 'root',
})
export class SocketioService {
  public message$: BehaviorSubject<string> = new BehaviorSubject('');
  socket: Socket<any>;

  constructor(
    private tokenStorage: TokenStorageService,
    private snackBar: MatSnackBar,
    private router: Router
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
    this.socket.on('message', (message: string) => {
      this.message$.next(message);
      console.log(message);
      // this.socket.emit('message', 'Hi there!');
    });
    this.socket.on('node-online', (data: any) => {
      console.log(data);
      // alert(`The node '${data.name}' just came online!`);
      this.openSuccessSnackBar(
        `The node '${data.name}' just came online!`,
        data
      );
    });
  }

  public sendMessage(message: string) {
    this.socket.emit('message', message);
  }

  public getMessages = () => {
    return this.message$.asObservable();
  };

  // Snackbar that opens with success background
  openSuccessSnackBar(msg: string, data: any) {
    const sb = this.snackBar.open(msg, 'View node', {
      verticalPosition: 'top',
      duration: 10000,
      panelClass: ['green-snackbar', 'login-snackbar'],
    });
    console.log(data);

    // define what happens if users click the button
    sb.onAction().subscribe(() => {
      this.router.navigate([`/node/${data.id}/view/${data.org_id}`]);
      console.log('button clicked!');
    });

    // // add a progress bar
    // sb.afterOpened().subscribe(() => {
    //   const duration = this.snackBar.containerInstance.snackBarConfig.duration;
    //     this.runProgressBar(duration);
    // });
  }

  //Snackbar that opens with failure background
  openFailureSnackBar() {
    this.snackBar.open('Invalid Login Credentials', 'Try again!', {
      duration: 6000,
      panelClass: ['red-snackbar', 'login-snackbar'],
    });
  }

  // runProgressBar(duration: number) {
  //   let progress = 100;
  //   const step = 0.005;
  //   this.cleanProgressBarInterval();
  //   this.currentIntervalId = setInterval(() => {
  //     this.progress -= 100 * step;
  //     if (this.progress < 0) {
  //       this.cleanProgressBarInterval();
  //     }
  //   }, duration * step);
  // }
}
