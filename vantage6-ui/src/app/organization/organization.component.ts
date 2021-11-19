import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';

import { API_URL } from '../constants';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['./organization.component.scss'],
})
export class OrganizationComponent implements OnInit {
  organization_details: any = null;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.getOrganizationDetails();
  }

  getOrganizationDetails(): void {
    this.http.get<any>(API_URL + 'organization/2').subscribe(
      (data) => {
        this.organization_details = data;
      },
      (err) => {
        console.log(err);
      }
    );
  }
}
