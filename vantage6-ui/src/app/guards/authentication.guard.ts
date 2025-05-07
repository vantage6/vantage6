import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { AuthGuardData, createAuthGuard } from 'keycloak-angular';
import { routePaths } from 'src/app/routes';

const isAccessAllowed = async (
  route: ActivatedRouteSnapshot,
  __: RouterStateSnapshot,
  authData: AuthGuardData
): Promise<boolean | UrlTree> => {
  const { authenticated } = authData;

  if (authenticated) {
    return true;
  } else {
    const router: Router = inject(Router);
    router.navigate([routePaths.login]);
    return false;
  }
};

export const authenticationGuard = createAuthGuard<CanActivateFn>(isAccessAllowed);
