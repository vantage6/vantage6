import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from 'src/app/auth/services/auth.service';

@Component({
  selector: 'app-setup-mfa',
  templateUrl: './setup-mfa.component.html',
  styleUrls: ['./setup-mfa.component.scss'],
})
export class SetupMfaComponent implements OnInit {
  qr_url: string;

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit(): void {
    if (this.authService.qr_uri === undefined) {
      this.router.navigateByUrl('/login');
    } else {
      this.qr_url = this.authService.qr_uri;
    }
  }
}
