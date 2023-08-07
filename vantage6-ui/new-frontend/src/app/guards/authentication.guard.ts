import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { routePaths } from '../routes';
import { AuthService } from '../services/auth.service';

export function authenticationGuard(): CanActivateFn {
  return async () => {
    const router: Router = inject(Router);
    const authService: AuthService = inject(AuthService);

    const isAuthenticated = await authService.isAuthenticated();
    if (!isAuthenticated) {
      router.navigate([routePaths.login]);
      return false;
    }
    return true;
  };
}
