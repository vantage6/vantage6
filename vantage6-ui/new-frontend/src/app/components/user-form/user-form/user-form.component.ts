import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { BaseOrganization, OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { Role } from 'src/app/models/api/role.model';
import { User, UserForm } from 'src/app/models/api/user.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { createCompareValidator } from 'src/app/validators/compare.validator';

@Component({
  selector: 'app-user-form',
  templateUrl: './user-form.component.html',
  styleUrls: ['./user-form.component.scss']
})
export class UserFormComponent implements OnInit, OnDestroy {
  @Input() user?: User;
  @Output() onCancel: EventEmitter<void> = new EventEmitter();
  @Output() onSubmit: EventEmitter<UserForm> = new EventEmitter();

  destroy$ = new Subject();
  form = this.fb.nonNullable.group(
    {
      username: ['', [Validators.required]],
      email: ['', [Validators.required]],
      password: [
        '',
        [
          Validators.required,
          Validators.minLength(8),
          Validators.pattern(/(?=.*[A-Z])/),
          Validators.pattern(/(?=.*[a-z])/),
          Validators.pattern(/(?=.*\d)/),
          Validators.pattern(/(?=.*\W)/)
        ]
      ],
      passwordRepeat: ['', [Validators.required]],
      firstname: '',
      lastname: '',
      organization_id: [NaN as number, [Validators.required]],
      roles: [{ value: [] as number[], disabled: true }, [Validators.required]]
    },
    { validators: [createCompareValidator('password', 'passwordRepeat')] }
  );
  isEdit: boolean = false;
  isLoading: boolean = true;
  organizations: BaseOrganization[] = [];
  roles: Role[] = [];

  constructor(
    private fb: FormBuilder,
    private organizationService: OrganizationService
  ) {}

  async ngOnInit(): Promise<void> {
    this.isEdit = !!this.user;
    if (this.isEdit && this.user) {
      this.form.controls.username.setValue(this.user.username);
      this.form.controls.email.setValue(this.user.email);
      this.form.controls.firstname.setValue(this.user.firstname);
      this.form.controls.lastname.setValue(this.user.lastname);
      this.form.controls.organization_id.setValue(this.user.organization?.id || NaN);
      this.form.controls.roles.setValue(this.user.roles.map((role) => role.id));
    }
    this.setupForm();
    await this.initData();
    if (this.isEdit) {
      await this.getRoles(this.form.controls.organization_id.value);
    }
    this.isLoading = false;
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  handleSubmit() {
    if (this.form.valid) {
      this.onSubmit.emit(this.form.getRawValue());
    }
  }

  handleCancel() {
    this.onCancel.emit();
  }

  private setupForm(): void {
    if (this.isEdit) {
      this.form.controls.password.disable();
      this.form.controls.passwordRepeat.disable();
      this.form.controls.organization_id.disable();
    }
    this.form.controls.organization_id.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (value) => {
      this.form.controls.roles.setValue([]);
      this.getRoles(value);
    });
  }

  private async initData(): Promise<void> {
    this.organizations = await this.organizationService.getOrganizations(OrganizationSortProperties.Name);
  }

  private async getRoles(organizationID: number): Promise<void> {
    this.roles = await this.organizationService.getRolesForOrganization(organizationID.toString());
    this.form.controls.roles.enable();
  }
}
