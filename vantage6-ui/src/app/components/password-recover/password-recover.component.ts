import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

import { environment } from 'src/environments/environment';

import { AuthService } from 'src/app/auth/services/auth.service';
import { TokenStorageService } from 'src/app/services/common/token-storage.service';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';

@Component({
  selector: 'app-password-recover',
  templateUrl: './password-recover.component.html',
  styleUrls: ['./password-recover.component.scss'],
})
export class PasswordRecoverComponent implements OnInit {
  form: any = {
    username: null,
    password: null,
  };
  isLoggedIn = false;

  constructor(
    private authService: AuthService,
    private tokenStorage: TokenStorageService,
    private userPermission: UserPermissionService,
    private router: Router
  ) {}

  ngOnInit(): void {
    if (this.tokenStorage.getToken()) {
      this.isLoggedIn = true;
    }
  }

  onSubmit(): void {
    const { username, password } = this.form;
  }
}
