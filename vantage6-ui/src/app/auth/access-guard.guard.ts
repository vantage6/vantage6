import { Injectable } from '@angular/core';
import { Router, ActivatedRouteSnapshot, CanActivate } from '@angular/router';

import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';

import { ModalService } from 'src/app/services/common/modal.service';
import { TokenStorageService } from 'src/app/services/common/token-storage.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { parseId } from 'src/app/shared/utils';
import { OpsType, ResType, ScopeType } from 'src/app/shared/enum';

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
      return false;
    }
    return true;
  }
}

@Injectable()
export class OrgAccessGuard implements CanActivate {
  isLoggedIn: boolean;

  constructor(
    private tokenStorage: TokenStorageService,
    private userPermission: UserPermissionService,
    private router: Router,
    private modalService: ModalService
  ) {
    this.isLoggedIn = false;
  }

  ngOnInit(): void {
    this.tokenStorage.isLoggedIn().subscribe((loggedIn: boolean) => {
      this.isLoggedIn = loggedIn;
    });
  }

  async canActivate(route: ActivatedRouteSnapshot): Promise<boolean> {
    if (!this.tokenStorage.loggedIn) {
      this.router.navigate(['login']);
    }
    const id = parseId(route.params.id) || null;
    const permissionType = route.data.permissionType || '*';

    // if id>0, we are editing an organization, otherwise creating
    // use the organization id to check whether logged in user is allowed to
    // edit/create organization.
    let permission: boolean = false;
    if (id && id > 0) {
      permission = await this.userPermission.async_can(
        permissionType,
        ResType.ORGANIZATION,
        id
      );
    }
    // second check if we are allowed to view organizations as part of collab
    // TODO somehow check if the organization we attempt to view is part of the collaboration
    if (!permission && permissionType === OpsType.VIEW) {
      permission = this.userPermission.hasPermission(
        OpsType.VIEW,
        ResType.ORGANIZATION,
        ScopeType.COLLABORATION
      );
    }
    if (!permission) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'You are not allowed to do that!',
      ]);
    }
    return permission;
  }
}

@Injectable()
export class AccessGuardByOrgId implements CanActivate {
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

  async canActivate(route: ActivatedRouteSnapshot): Promise<boolean> {
    if (!this.tokenStorage.loggedIn) {
      this.router.navigate(['login']);
    }
    const org_id = parseId(route.params.org_id) || null;
    const permissionType = route.data.permissionType || '*';
    const permissionResource = route.data.permissionResource || '*';

    // if id>0, we are editing an organization, otherwise creating
    // use the organization id to check whether logged in user is allowed to
    // edit/create organization.
    let permission: boolean = false;
    if (org_id && org_id > 0) {
      permission = await this.userPermission.async_can(
        permissionType,
        permissionResource,
        org_id
      );
    }
    return permission;
  }
}
