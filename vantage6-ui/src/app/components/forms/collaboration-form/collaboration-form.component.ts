import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatSelectChange, MatSelect } from '@angular/material/select';
import { Subject, takeUntil } from 'rxjs';
import { compareObjIDs } from 'src/app/helpers/general.helper';
import { Collaboration, CollaborationForm } from 'src/app/models/api/collaboration.model';
import { BaseOrganization, OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { PermissionService } from 'src/app/services/permission.service';
import { NgIf, NgFor } from '@angular/common';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatOption } from '@angular/material/core';
import { MatButton } from '@angular/material/button';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-collaboration-form',
  templateUrl: './collaboration-form.component.html',
  imports: [
    NgIf,
    ReactiveFormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatCheckbox,
    MatSelect,
    NgFor,
    MatOption,
    MatButton,
    MatProgressSpinner,
    TranslateModule
  ],
  styleUrls: ['./collaboration-form.component.scss']
})
export class CollaborationFormComponent implements OnInit {
  @Input() collaboration?: Collaboration;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<CollaborationForm> = new EventEmitter();
  destroy$ = new Subject();

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    encrypted: false,
    session_restrict_to_same_image: false,
    organizations: [[] as BaseOrganization[], [Validators.required]],
    registerNodes: true
  });

  isEdit: boolean = false;
  canEditOrganizations: boolean = false;
  isLoading: boolean = true;
  newOrganizations: BaseOrganization[] = [];
  organizations: BaseOrganization[] = [];
  compareOrganizationsForSelection = compareObjIDs;

  constructor(
    private fb: FormBuilder,
    private organizationService: OrganizationService,
    private permissionService: PermissionService
  ) {}

  async ngOnInit(): Promise<void> {
    this.isEdit = !!this.collaboration;
    this.setPermissions();
    if (this.collaboration) {
      this.form.controls.name.setValue(this.collaboration.name);
      this.form.controls.encrypted.setValue(this.collaboration.encrypted);
      this.form.controls.session_restrict_to_same_image.setValue(this.collaboration.session_restrict_to_same_image);
      this.form.controls.organizations.setValue(this.collaboration.organizations);
    }
    await this.initData();
    this.isLoading = false;
  }

  get newOrganizationNames() {
    return this.newOrganizations.map((organization) => organization.name).join(', ');
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canEditOrganizations =
            !this.isEdit || this.permissionService.isAllowed(ScopeType.GLOBAL, ResourceType.COLLABORATION, OperationType.EDIT);
        }
      });
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
