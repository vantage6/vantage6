import { Component, OnInit, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatSidenav } from '@angular/material/sidenav';
import { delay } from 'rxjs/operators';

import { TokenStorageService } from 'src/app/services/common/token-storage.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { getEmptyUser, User } from 'src/app/interfaces/user';

@Component({
  selector: 'app-navbar',
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.scss'],
})
export class NavbarComponent implements OnInit {
  loggedin_user: User = getEmptyUser();

  @ViewChild(MatSidenav)
  sidenav!: MatSidenav;

  constructor(
    private observer: BreakpointObserver,
    private tokenStorage: TokenStorageService,
    public userPermission: UserPermissionService,
    private router: Router
  ) {
    this.userPermission.getUser().subscribe((user) => {
      this.loggedin_user = user;
    });
  }

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
    this.router.navigateByUrl('/login');
  }
}
