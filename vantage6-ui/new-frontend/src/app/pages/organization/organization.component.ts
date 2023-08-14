import { Component, OnInit } from '@angular/core';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['./organization.component.scss']
})
export class OrganizationComponent implements OnInit {
  organizations: BaseOrganization[] = [];

  constructor(private organizationService: OrganizationService) {}

  async ngOnInit(): Promise<void> {
    this.organizations = await this.organizationService.getOrganizations();
  }
}
