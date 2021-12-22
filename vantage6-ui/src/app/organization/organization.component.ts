import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { map, mergeMap, switchMap } from 'rxjs/operators';

import { environment } from 'src/environments/environment';

import { UserPermissionService } from '../services/user-permission.service';

interface Role {
  id: number;
}

interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  roles: Role[];
  rules: string[];
}

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
    private http: HttpClient,
    private userPermission: UserPermissionService
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
    this.http
      .get<any>(environment.api_url + '/user/' + this.userId)
      .pipe(
        mergeMap((user_data) =>
          this.http.get(
            environment.api_url + '/organization/' + user_data.organization.id
          )
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
    for (let user of this.organization_details.users) {
      this.http.get(environment.server_url + user.link).subscribe(
        (data: any) => {
          console.log(data);
          let roles: Role[] = [];
          if (data.roles) {
            data.roles.forEach((role: any) => {
              roles.push({ id: role.id });
            });
          }
          this.organization_users.push({
            id: data.id,
            first_name: data.firstname,
            last_name: data.lastname,
            email: data.email,
            roles: roles,
            rules: data.rules,
          });
        },
        (error) => {
          console.log(error);
        }
      );
    }
  }
}
