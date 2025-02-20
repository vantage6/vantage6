import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { readFile } from 'src/app/helpers/file.helper';
import { Organization, OrganizationCreate } from 'src/app/models/api/organization.model';
import { MatFormField, MatLabel, MatSuffix } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { NgIf } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-organization-form',
  templateUrl: './organization-form.component.html',
  standalone: true,
  imports: [ReactiveFormsModule, MatFormField, MatLabel, MatInput, NgIf, MatButton, MatSuffix, TranslateModule]
})
export class OrganizationFormComponent implements OnInit {
  @Input() organization?: Organization;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<OrganizationCreate> = new EventEmitter();

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    address1: '',
    address2: '',
    country: '',
    domain: '',
    public_key: ''
  });
  selectedFile: File | null = null;

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    if (this.organization) {
      this.form.controls.name.setValue(this.organization.name);
      this.form.controls.address1.setValue(this.organization.address1);
      this.form.controls.address2.setValue(this.organization.address2);
      this.form.controls.country.setValue(this.organization.country);
      this.form.controls.domain.setValue(this.organization.domain);
      this.form.controls.public_key.setValue(this.organization.public_key || '');
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

  async selectFile(event: Event) {
    this.selectedFile = (event.target as HTMLInputElement).files?.item(0) || null;

    if (!this.selectedFile) return;
    const fileData = await readFile(this.selectedFile);

    this.form.controls.public_key.setValue(fileData || '');
  }
}
