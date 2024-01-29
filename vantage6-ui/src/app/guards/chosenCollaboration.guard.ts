import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { routePaths } from '../routes';
import { CHOSEN_COLLABORATION } from '../models/constants/sessionStorage';

export function chosenCollaborationGuard(): CanActivateFn {
  return async () => {
    const router: Router = inject(Router);

    const chosenCollaboration = sessionStorage.getItem(CHOSEN_COLLABORATION);
    if (!chosenCollaboration) {
      router.navigate([routePaths.start]);
      return false;
    }
    return true;
  };
}
