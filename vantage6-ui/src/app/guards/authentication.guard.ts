import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { AuthResult } from 'src/app/models/api/auth.model';

export function authenticationGuard(): CanActivateFn {
  return async () => {
    const router: Router = inject(Router);
    const authService: AuthService = inject(AuthService);

    const isAuthenticated = await authService.isAuthenticated();
    if (isAuthenticated !== AuthResult.Success) {
      router.navigate([routePaths.login]);
      return false;
    }
    return true;
  };
}
