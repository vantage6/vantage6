import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { BaseOrganization, Organization } from 'src/app/models/api/organization.model';
import { RoleForm } from 'src/app/models/api/role.model';
import { Rule, Rule_ } from 'src/app/models/api/rule.model';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatSelect } from '@angular/material/select';
import { NgFor } from '@angular/common';
import { MatOption } from '@angular/material/core';
import { PermissionsMatrixServerComponent } from '../../permissions-matrix/server/permissions-matrix-server.component';
import { RoleSubmitButtonsComponent } from '../../helpers/role-submit-buttons/role-submit-buttons.component';
import { TranslateModule } from '@ngx-translate/core';
import { OrderByPipe } from '../../../pipes/order-by.pipe';

@Component({
    selector: 'app-role-form',
    templateUrl: './role-form.component.html',
    styleUrls: ['./role-form.component.scss'],
    imports: [
        ReactiveFormsModule,
        MatFormField,
        MatLabel,
        MatInput,
        MatSelect,
        NgFor,
        MatOption,
        PermissionsMatrixServerComponent,
        RoleSubmitButtonsComponent,
        TranslateModule,
        OrderByPipe
    ]
})
export class RoleFormComponent {
  @Input() selectableRules: Rule[] = [];
  @Input() organizations: Organization[] | BaseOrganization[] = [];
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<RoleForm> = new EventEmitter();

  constructor(private fb: FormBuilder) {}

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: '',
    organization_id: [0, [Validators.required]]
  });

  selectedRules: number[] = [];

  handleSubmit() {
    if (this.form.valid) {
      this.submitted.emit({ ...this.form.getRawValue(), rules: this.selectedRules });
    }
  }

  handleCancel() {
    this.cancelled.emit();
  }

  handleChangedSelection(rules: Rule_[]): void {
    // we know that these are vantage6 server rules, not store rules here
    rules = rules as Rule[];
    this.selectedRules = rules ? rules.map((rule) => rule.id) : [];
  }

  get submitDisabled(): boolean {
    return this.selectedRules?.length === 0;
  }
}
