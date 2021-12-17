import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { map, mergeMap, switchMap } from 'rxjs/operators';

import { environment } from 'src/environments/environment';

import { UserPermissionService } from '../services/user-permission.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['./organization.component.scss'],
})
export class OrganizationComponent implements OnInit {
  organization_details: any = null;
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
          console.log(data);
        },
        (err) => {
          console.log(err);
        }
      );
  }
}
