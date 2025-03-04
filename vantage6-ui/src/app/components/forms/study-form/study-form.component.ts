import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatSelectChange, MatSelect } from '@angular/material/select';
import { compareObjIDs } from 'src/app/helpers/general.helper';
import { BaseOrganization, OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { Study, StudyForm } from 'src/app/models/api/study.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { NgIf, NgFor } from '@angular/common';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption } from '@angular/material/core';
import { MatButton } from '@angular/material/button';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

@Component({
    selector: 'app-study-form',
    templateUrl: './study-form.component.html',
    styleUrls: ['./study-form.component.scss'],
    imports: [
        NgIf,
        ReactiveFormsModule,
        MatFormField,
        MatLabel,
        MatInput,
        MatSelect,
        NgFor,
        MatOption,
        MatButton,
        MatProgressSpinner,
        TranslateModule
    ]
})
export class StudyFormComponent implements OnInit {
  @Input() study?: Study;
  @Input() collaborationId?: string;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<StudyForm> = new EventEmitter();

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    organizations: [[] as BaseOrganization[], [Validators.required]]
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
    this.isEdit = !!this.study;
    if (this.study) {
      this.form.controls.name.setValue(this.study.name);
      this.form.controls.organizations.setValue(this.study.organizations);
    }
    await this.initData();
    this.isLoading = false;
  }

  get newOrganizationNames() {
    return this.newOrganizations.map((organization) => organization.name).join(', ');
  }

  async handleOrganizationChange(e: MatSelectChange): Promise<void> {
    if (this.isEdit) {
      const newOrganizationsIDs = e.value.filter((id: number) => !this.study?.organizations.find((organization) => organization.id === id));
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
    this.organizations = await this.organizationService.getOrganizations({
      sort: OrganizationSortProperties.Name,
      collaboration_id: this.collaborationId
    });
  }
}
