import { Component, OnInit } from '@angular/core';

import { UserPermissionService } from '../services/user-permission.service';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {
  permissions: any[] = [];

  constructor(private userPermission: UserPermissionService) {}

  ngOnInit() {
    this.permissions = this.userPermission.getPermissions();
  }
}
