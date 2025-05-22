import { Injectable, inject, effect } from '@angular/core';
import Keycloak from 'keycloak-js';
import { KEYCLOAK_EVENT_SIGNAL, KeycloakEventType, typeEventArgs, ReadyArgs } from 'keycloak-angular';
import { BehaviorSubject, Observable } from 'rxjs';

// import { PermissionService } from './permission.service';
import { SocketioConnectService } from './socketio-connect.service';
// import { EncryptionService } from './encryption.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  username = '';
  password = '';
  qr_uri = '';
  otp_code = '';

  authenticated = false;
  authenticated$ = new BehaviorSubject<boolean>(false);
  keycloakStatus: string | undefined;
  private readonly keycloak = inject(Keycloak);
  private readonly keycloakSignal = inject(KEYCLOAK_EVENT_SIGNAL);

  constructor(
    // private permissionService: PermissionService,
    private socketConnectService: SocketioConnectService
    // private storePermissionService: PermissionService,
    // private encryptionService: EncryptionService
  ) {
    effect(() => {
      const keycloakEvent = this.keycloakSignal();

      this.keycloakStatus = keycloakEvent.type;

      if (keycloakEvent.type === KeycloakEventType.Ready) {
        this.authenticated = typeEventArgs<ReadyArgs>(keycloakEvent.args);
        this.authenticated$.next(this.authenticated);
      }

      if (keycloakEvent.type === KeycloakEventType.AuthLogout) {
        this.authenticated = false;
        this.authenticated$.next(this.authenticated);
      }
    });
  }

  // TODO connect socket
  // async isAuthenticated(): Promise<AuthResult> {
  //   if (authResult === AuthResult.Success) {
  //     this.socketConnectService.connect();
  //   }
  //   return authResult;
  // }

  authenticatedObservable(): Observable<boolean> {
    return this.authenticated$.asObservable();
  }

  async login(): Promise<void> {
    this.keycloak.login();
  }

  logout(): void {
    // this.permissionService.clear();
    // this.storePermissionService.clear();
    this.socketConnectService.disconnect();
    // this.encryptionService.clear();
    this.keycloak.logout();
  }
}
