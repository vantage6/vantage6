import { Component, ViewChild } from '@angular/core';
import { MatSidenav } from '@angular/material/sidenav';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent {
  isLoggedIn: boolean;
  showAdminBoard = false;
  showModeratorBoard = false;
  username?: string;

  @ViewChild(MatSidenav)
  sidenav!: MatSidenav;

  constructor(private authService: AuthService) {
    this.isLoggedIn = false;
  }

  ngOnInit(): void {
    this.authService.isLoggedIn().subscribe((loggedIn: boolean) => {
      this.isLoggedIn = loggedIn;
    });
  }
}
