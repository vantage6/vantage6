import { Injectable } from '@angular/core';
import { AuthService } from './auth.service';
import { SocketioConnectService } from './socketio-connect.service';
import { PermissionService } from './permission.service';
import { EncryptionService } from './encryption.service';
import { StorePermissionService } from './store-permission.service';
import { KeycloakUserService } from './keycloak-user.service';

@Injectable({
  providedIn: 'root'
})
export class LoginLogoutService {
  constructor(
    private authService: AuthService,
    private socketConnectService: SocketioConnectService,
    private permissionService: PermissionService,
    private storePermissionService: StorePermissionService,
    private encryptionService: EncryptionService,
    private keycloakUserService: KeycloakUserService
  ) {
    this.authService.authenticatedObservable().subscribe((loggedIn: boolean) => {
      if (loggedIn) {
        this.onLogin();
      }
    });
  }

  onLogin() {
    this.socketConnectService.connect();
  }

  // TODO v5+ this should be more efficient - not sure asyncs are needed
  async logout() {
    await this.permissionService.clear();
    await this.storePermissionService.clear();
    await this.encryptionService.clear();
    await this.socketConnectService.disconnect();
    this.authService.logout();
    this.keycloakUserService.clearProfile();
  }
}
