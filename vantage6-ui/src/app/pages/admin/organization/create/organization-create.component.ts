import { Component, HostBinding } from '@angular/core';
import { Router } from '@angular/router';
import { OrganizationCreate } from 'src/app/models/api/organization.model';
import { routePaths } from 'src/app/routes';
import { OrganizationService } from 'src/app/services/organization.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf } from '@angular/common';
import { MatCard, MatCardContent } from '@angular/material/card';
import { OrganizationFormComponent } from '../../../../components/forms/organization-form/organization-form.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-organization-create',
  templateUrl: './organization-create.component.html',
  standalone: true,
  imports: [PageHeaderComponent, NgIf, MatCard, MatCardContent, OrganizationFormComponent, MatProgressSpinner, TranslateModule]
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
