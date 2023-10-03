import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { MatSelectChange } from '@angular/material/select';
import { Collaboration, CollaborationForm } from 'src/app/models/api/collaboration.model';
import { BaseOrganization, OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-collaboration-form',
  templateUrl: './collaboration-form.component.html',
  styleUrls: ['./collaboration-form.component.scss']
})
export class CollaborationFormComponent implements OnInit {
  @Input() collaboration?: Collaboration;
  @Output() onCancel: EventEmitter<void> = new EventEmitter();
  @Output() onSubmit: EventEmitter<CollaborationForm> = new EventEmitter();

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    encrypted: false,
    organization_ids: [[] as number[], [Validators.required]],
    registerNodes: true
  });

  isEdit: boolean = false;
  isLoading: boolean = true;
  newOrganizations: BaseOrganization[] = [];
  organizations: BaseOrganization[] = [];

  constructor(
    private fb: FormBuilder,
    private organizationService: OrganizationService
  ) {}

  async ngOnInit(): Promise<void> {
    this.isEdit = !!this.collaboration;
    if (this.collaboration) {
      this.form.controls.name.setValue(this.collaboration.name);
      this.form.controls.encrypted.setValue(this.collaboration.encrypted);
      this.form.controls.organization_ids.setValue(this.collaboration.organizations.map((organization) => organization.id));
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
      this.onSubmit.emit(this.form.getRawValue());
    }
  }

  handleCancel() {
    this.onCancel.emit();
  }

  private async initData(): Promise<void> {
    this.organizations = await this.organizationService.getOrganizations({ sort: OrganizationSortProperties.Name });
  }
}
