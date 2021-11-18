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
    });
  }

  canActivate(route: ActivatedRouteSnapshot): boolean {
    const requiresLogin = route.data.requiresLogin || false;
    if (requiresLogin && !this.authService.loggedIn) {
      this.router.navigate(['login']);
    }
    return true;
  }
}
