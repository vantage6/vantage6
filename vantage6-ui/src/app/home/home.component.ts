import { Component, OnInit } from '@angular/core';

import { UserPermissionService } from '../services/user-permission.service';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {
  permissions: string[] = [];

  constructor(private userPermission: UserPermissionService) {}

  ngOnInit() {
    this.userPermission.getUserRules().subscribe((rules: string[]) => {
      this.permissions = rules;
    });
  }
}
