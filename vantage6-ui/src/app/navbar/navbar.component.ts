import { Component, OnInit, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatSidenav } from '@angular/material/sidenav';
import { delay } from 'rxjs/operators';

import { TokenStorageService } from '../services/token-storage.service';
import { UserPermissionService } from '../services/user-permission.service';

@Component({
  selector: 'app-navbar',
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.scss'],
})
export class NavbarComponent implements OnInit {
  isLoggedIn = true; // TODO remove

  @ViewChild(MatSidenav)
  sidenav!: MatSidenav;

  constructor(
    private observer: BreakpointObserver,
    private tokenStorage: TokenStorageService,
    private userPermission: UserPermissionService,
    private router: Router
  ) {}

  ngOnInit(): void {}

  ngAfterViewInit() {
    this.observer
      .observe(['(max-width: 800px)'])
      .pipe(delay(1))
      .subscribe((res) => {
        if (res.matches) {
          this.sidenav.mode = 'over';
          this.sidenav.close();
        } else {
          this.sidenav.mode = 'side';
          this.sidenav.open();
        }
      });
  }

  logout(): void {
    this.tokenStorage.signOut();
    this.userPermission.clearPermissions();
    this.router.navigateByUrl('/login');
  }
}
