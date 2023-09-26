import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { MatSelectChange } from '@angular/material/select';
import { Router } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { BaseOrganization, OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { Role } from 'src/app/models/api/role.model';
import { UserCreate } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { OrganizationService } from 'src/app/services/organization.service';
import { UserService } from 'src/app/services/user.service';
import { createCompareValidator } from 'src/app/validators/compare.validator';

@Component({
  selector: 'app-user-create',
  templateUrl: './user-create.component.html',
  styleUrls: ['./user-create.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class UserCreateComponent implements OnInit, OnDestroy {
  destroy$ = new Subject();
  routes = routePaths;

  isLoading: boolean = true;
  isSubmitting: boolean = false;
  organizations: BaseOrganization[] = [];
  roles: Role[] = [];

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
      firstName: '',
      lastName: '',
      organizationID: ['', [Validators.required]],
      roleIDs: [{ value: [] as number[], disabled: true }, [Validators.required]]
    },
    { validators: [createCompareValidator('password', 'passwordRepeat')] }
  );

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private organizationService: OrganizationService,
    private userService: UserService
  ) {}

  ngOnInit(): void {
    this.setupForm();
    this.initData();
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  async handleSubmit(): Promise<void> {
    if (this.form.valid) {
      this.isSubmitting = true;
      const data = this.form.getRawValue();
      const userCreate: UserCreate = {
        username: data.username,
        email: data.email,
        password: data.password,
        firstname: data.firstName,
        lastname: data.lastName,
        organization_id: Number.parseInt(data.organizationID),
        roles: data.roleIDs
      };
      const user = await this.userService.createUser(userCreate);
      if (user.id) {
        this.router.navigate([routePaths.users]);
      } else {
        this.isSubmitting = false;
      }
    }
  }

  private setupForm(): void {
    this.form.controls.organizationID.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (value) => {
      this.form.controls.roleIDs.setValue([]);
      this.roles = await this.organizationService.getRolesForOrganization(value);
      this.form.controls.roleIDs.enable();
    });
  }

  private async initData(): Promise<void> {
    this.organizations = await this.organizationService.getOrganizations(OrganizationSortProperties.Name);
    this.isLoading = false;
  }
}
