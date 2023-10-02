import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Organization, OrganizationCreate } from 'src/app/models/api/organization.model';

@Component({
  selector: 'app-organization-form',
  templateUrl: './organization-form.component.html',
  styleUrls: ['./organization-form.component.scss']
})
export class OrganizationFormComponent implements OnInit {
  @Output() onCancel: EventEmitter<void> = new EventEmitter();
  @Output() onSubmit: EventEmitter<OrganizationCreate> = new EventEmitter();
  @Input() organization?: Organization;

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    address1: '',
    address2: '',
    country: '',
    domain: ''
  });

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    if (this.organization) {
      this.form.patchValue(this.organization);
    }
  }

  async handleSubmit() {
    if (this.form.valid) {
      this.onSubmit.emit(this.form.getRawValue());
    }
  }

  handleCancel() {
    this.onCancel.emit();
  }
}
