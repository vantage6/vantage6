import { Component, OnInit, ViewChild } from '@angular/core';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatSidenav } from '@angular/material/sidenav';
import { delay } from 'rxjs/operators';

import { AuthService } from '../services/auth.service';

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
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    // this.authService.isLoggedIn().subscribe((loggedIn: boolean) => {
    //   this.isLoggedIn = loggedIn;
    //   console.log('logged in', this.isLoggedIn);
    // });
    // this.isLoggedIn = !!this.tokenStorageService.getToken();
    // if (this.isLoggedIn) {
    //   const user = this.tokenStorageService.getUser();
    // this.roles = user.roles;
    // this.showAdminBoard = this.roles.includes('ROLE_ADMIN');
    // this.showModeratorBoard = this.roles.includes('ROLE_MODERATOR');
    // this.username = user.username;
    // }
  }

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
    // this.tokenStorageService.signOut();
    this.authService.signOut();
    window.location.reload();
  }
}
