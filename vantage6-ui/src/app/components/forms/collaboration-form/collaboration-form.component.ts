import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { MatSelectChange } from '@angular/material/select';
import { compareObjIDs } from 'src/app/helpers/general.helper';
import { Collaboration, CollaborationForm } from 'src/app/models/api/collaboration.model';
import { BaseOrganization, Organization, OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-collaboration-form',
  templateUrl: './collaboration-form.component.html'
})
export class CollaborationFormComponent implements OnInit {
  @Input() collaboration?: Collaboration;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<CollaborationForm> = new EventEmitter();

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    encrypted: false,
    organizations: [[] as BaseOrganization[], [Validators.required]],
    registerNodes: true
  });

  isEdit: boolean = false;
  isLoading: boolean = true;
  newOrganizations: BaseOrganization[] = [];
  organizations: BaseOrganization[] = [];
  compareOrganizationsForSelection = compareObjIDs;

  constructor(
    private fb: FormBuilder,
    private organizationService: OrganizationService
  ) {}

  async ngOnInit(): Promise<void> {
    this.isEdit = !!this.collaboration;
    if (this.collaboration) {
      this.form.controls.name.setValue(this.collaboration.name);
      this.form.controls.encrypted.setValue(this.collaboration.encrypted);
      this.form.controls.organizations.setValue(this.collaboration.organizations);
    }
    await this.initData();
    this.isLoading = false;
  }

  get newOrganizationNames() {
    return this.newOrganizations.map((organization) => organization.name).join(', ');
  }

  async handleOrganizationChange(e: MatSelectChange): Promise<void> {
    if (this.isEdit) {
      const newOrganizationsIDs = e.value.filter(
        (id: number) => !this.collaboration?.organizations.find((organization) => organization.id === id)
      );
      this.newOrganizations = this.organizations.filter((organization) => newOrganizationsIDs.includes(organization.id));
    }
  }

  handleSubmit() {
    if (this.form.valid) {
      this.submitted.emit(this.form.getRawValue());
    }
  }

  handleCancel() {
    this.cancelled.emit();
  }

  private async initData(): Promise<void> {
    this.organizations = await this.organizationService.getOrganizations({ sort: OrganizationSortProperties.Name });
  }
}
