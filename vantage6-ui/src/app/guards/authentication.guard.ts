import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, RouterStateSnapshot, UrlTree } from '@angular/router';
import { AuthGuardData, createAuthGuard } from 'keycloak-angular';
import { AuthService } from '../services/auth.service';
import { firstValueFrom } from 'rxjs';

const isAccessAllowed = async (
  route: ActivatedRouteSnapshot,
  __: RouterStateSnapshot,
  authData: AuthGuardData
): Promise<boolean | UrlTree> => {
  const { authenticated } = authData;

  if (authenticated) {
    return true;
  } else {
    const authService = inject(AuthService);
    await authService.login();
    return firstValueFrom(authService.authenticatedObservable());
  }
};

export const authenticationGuard = createAuthGuard<CanActivateFn>(isAccessAllowed);
