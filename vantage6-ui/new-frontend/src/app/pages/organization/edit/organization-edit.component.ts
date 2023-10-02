import { Component, Input } from '@angular/core';
import { Router } from '@angular/router';
import { Organization, OrganizationCreate } from 'src/app/models/api/organization.model';
import { routePaths } from 'src/app/routes';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-organization-edit',
  templateUrl: './organization-edit.component.html',
  styleUrls: ['./organization-edit.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class OrganizationEditComponent {
  @Input() id: string = '';

  isLoading: boolean = true;
  isSubmitting: boolean = false;
  organization?: Organization;

  constructor(
    private router: Router,
    private organizationService: OrganizationService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
  }

  async handleSubmit(organizationCreate: OrganizationCreate) {
    this.isSubmitting = true;
    const result = await this.organizationService.editOrganization(this.id, organizationCreate);
    if (result?.id) {
      this.router.navigate([routePaths.organization, this.id]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel() {
    this.router.navigate([routePaths.organization, this.id]);
  }

  private async initData(): Promise<void> {
    this.organization = await this.organizationService.getOrganization(this.id);
    this.isLoading = false;
  }
}
