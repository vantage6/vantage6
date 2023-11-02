import { Component, HostBinding } from '@angular/core';
import { Router } from '@angular/router';
import { OrganizationCreate } from 'src/app/models/api/organization.model';
import { routePaths } from 'src/app/routes';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-organization-create',
  templateUrl: './organization-create.component.html',
  styleUrls: ['./organization-create.component.scss']
})
export class OrganizationCreateComponent {
  @HostBinding('class') class = 'card-container';
  isSubmitting = false;

  constructor(
    private router: Router,
    private organizationService: OrganizationService
  ) {}

  async handleSubmit(organization: OrganizationCreate) {
    this.isSubmitting = true;
    const result = await this.organizationService.createOrganization(organization);
    if (result?.id) {
      this.router.navigate([routePaths.organization]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel() {
    this.router.navigate([routePaths.organizations]);
  }
}
