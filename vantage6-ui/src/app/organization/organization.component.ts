import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { map, mergeMap, switchMap } from 'rxjs/operators';

import { API_URL } from '../constants';
import { TokenStorageService } from '../services/token-storage.service';
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
    private tokenStorage: TokenStorageService,
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
      .get<any>(API_URL + '/user/' + this.userId)
      .pipe(
        mergeMap((user_data) =>
          this.http.get(API_URL + '/organization/' + user_data.organization.id)
        )
      )
      .subscribe(
        (data) => {
          this.organization_details = data;
        },
        (err) => {
          console.log(err);
        }
      );
  }
}
