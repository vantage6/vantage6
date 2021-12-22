import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { mergeMap } from 'rxjs/operators';

import { environment } from 'src/environments/environment';

import { User } from '../interfaces/user';
import { Role } from '../interfaces/role';

import { UserPermissionService } from '../services/user-permission.service';
import { UserService } from '../services/api/user.service';
import { OrganizationService } from '../services/api/organization.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['./organization.component.scss'],
})
export class OrganizationComponent implements OnInit {
  organization_details: any = null;
  organization_users: User[] = [];
  userId: number = 0;

  constructor(
    private userPermission: UserPermissionService,
    private userService: UserService,
    private organizationService: OrganizationService
  ) {}

  ngOnInit(): void {
    this.userPermission.getUserId().subscribe((id) => {
      this.userId = id;
      this.getOrganizationDetails();
    });
  }

  getOrganizationDetails(): void {
    if (this.userId === 0) return;
    // first obtain user information to get organization id, then obtain
    // organization information
    this.userService
      .get(this.userId)
      .pipe(
        mergeMap((user_data) =>
          this.organizationService.get(user_data.organization.id)
        )
      )
      .subscribe(
        (data) => {
          this.organization_details = data;
          this.collectUsers();
        },
        (err) => {
          console.log(err);
        }
      );
  }

  collectUsers(): void {
    this.organization_users = [];
    this.userService.list(this.organization_details.id).subscribe(
      (data: any) => {
        for (let user of data) {
          let roles: Role[] = [];
          if (user.roles) {
            user.roles.forEach((role: any) => {
              roles.push({ id: role.id });
            });
          }
          this.organization_users.push({
            id: user.id,
            first_name: user.firstname,
            last_name: user.lastname,
            email: user.email,
            roles: roles,
            rules: user.rules,
          });
        }
      },
      (error) => {
        console.log(error);
      }
    );
  }
}
