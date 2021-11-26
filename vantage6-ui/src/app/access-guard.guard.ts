import { Injectable } from '@angular/core';
import { Router, ActivatedRouteSnapshot, CanActivate } from '@angular/router';

import { TokenStorageService } from './services/token-storage.service';
import { UserPermissionService } from './services/user-permission.service';

@Injectable()
export class AccessGuard implements CanActivate {
  isLoggedIn: boolean;

  constructor(
    private tokenStorage: TokenStorageService,
    private userPermission: UserPermissionService,
    private router: Router
  ) {
    this.isLoggedIn = false;
  }

  ngOnInit(): void {
    this.tokenStorage.isLoggedIn().subscribe((loggedIn: boolean) => {
      this.isLoggedIn = loggedIn;
    });
  }

  canActivate(route: ActivatedRouteSnapshot): boolean {
    const requiresLogin = route.data.requiresLogin || false;
    if (requiresLogin && !this.tokenStorage.loggedIn) {
      this.router.navigate(['login']);
    }
    const permType = route.data.permissionType || '*';
    const permResource = route.data.permissionResource || '*';
    const permScope = route.data.permissionScope || '*';
    if (!this.userPermission.hasPermission(permType, permResource, permScope)) {
      alert('No permission!'); // TODO improve?!
      return false;
    }
    return true;
  }
}
