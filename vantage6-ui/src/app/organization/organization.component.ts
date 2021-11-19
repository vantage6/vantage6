import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';

import { API_URL } from '../constants';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['./organization.component.scss'],
})
export class OrganizationComponent implements OnInit {
  // token: string | null;

  constructor(private http: HttpClient, private authService: AuthService) {
    // this.token = authService.getToken();
  }

  ngOnInit(): void {
    this.getOrganizationDetails();
  }

  getOrganizationDetails(): void {
    // TODO use token, see eg
    // https://stackoverflow.com/questions/48017603/angular-sending-token-with-get-and-other-requests
    // console.log(this.token);
    this.http.get<any>(API_URL + 'organization/1').subscribe(
      (data) => {
        console.log(data);
      },
      (err) => {
        console.log(err);
      }
    );
  }
}
