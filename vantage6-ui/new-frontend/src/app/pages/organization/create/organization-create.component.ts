import { Component } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { routePaths } from 'src/app/routes';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-organization-create',
  templateUrl: './organization-create.component.html',
  styleUrls: ['./organization-create.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class OrganizationCreateComponent {
  routes = routePaths;

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    address1: '',
    address2: '',
    country: '',
    domain: ''
  });
  isSubmitting = false;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private organizationService: OrganizationService
  ) {}

  async handleSubmit() {
    if (this.form.valid) {
      this.isSubmitting = true;
      const result = await this.organizationService.createOrganization(this.form.getRawValue());
      if (result?.id) {
        this.router.navigate([routePaths.organization]);
      } else {
        this.isSubmitting = false;
      }
    }
  }
}
