import { Injectable } from '@angular/core';
import { AuthService } from './auth.service';
import { SocketioConnectService } from './socketio-connect.service';
import { PermissionService } from './permission.service';
import { EncryptionService } from './encryption.service';
import { StorePermissionService } from './store-permission.service';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class OnLoginStatusChangeService {
  authenticationComplete$ = new BehaviorSubject<boolean>(false);

  constructor(
    private authService: AuthService,
    private socketConnectService: SocketioConnectService,
    private permissionService: PermissionService,
    private storePermissionService: StorePermissionService,
    private encryptionService: EncryptionService
  ) {
    this.authService.authenticatedObservable().subscribe((loggedIn: boolean) => {
      if (loggedIn) {
        this.onLogin();
      } else {
        this.onLogout();
      }
    });
  }

  authenticateCompleteObservable(): Observable<boolean> {
    return this.authenticationComplete$.asObservable();
  }

  onLogin() {
    this.socketConnectService.connect();
    this.authenticationComplete$.next(true);
  }

  onLogout() {
    this.permissionService.clear();
    this.storePermissionService.clear();
    this.encryptionService.clear();
    this.socketConnectService.disconnect();
    this.authenticationComplete$.next(false);
  }
}
