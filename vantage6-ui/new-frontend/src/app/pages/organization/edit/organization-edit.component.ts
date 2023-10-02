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
    this.isLoading = false;
  }

  async handleSubmit(organizationCreate: OrganizationCreate) {
    if (!this.organization) return;

    this.isSubmitting = true;
    const result = await this.organizationService.editOrganization(this.organization?.id.toString(), organizationCreate);
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
  }
}
