import { Injectable } from '@angular/core';
import {
  Router,
  ActivatedRouteSnapshot,
  CanActivate,
  RouterStateSnapshot,
  UrlTree,
} from '@angular/router';

import { AuthService } from './services/auth.service';

@Injectable()
export class AccessGuard implements CanActivate {
  isLoggedIn: boolean;

  constructor(private authService: AuthService, private router: Router) {
    this.isLoggedIn = false;
  }

  ngOnInit(): void {
    this.authService.isLoggedIn().subscribe((loggedIn: boolean) => {
      this.isLoggedIn = loggedIn;
      console.log('logged in from guard', this.isLoggedIn);
    });
  }

  canActivate(route: ActivatedRouteSnapshot): boolean {
    console.log('can activate?');
    const requiresLogin = route.data.requiresLogin || false;
    if (requiresLogin) {
      console.log('here');
      if (!this.authService.loggedIn) {
        console.log('not logged in');
        this.router.navigate(['login']);
      } else {
        console.log('logged in');
      }
    }
    return true;
  }
}
