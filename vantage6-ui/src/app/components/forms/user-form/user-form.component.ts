import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { takeUntil } from 'rxjs';
import { BaseOrganization, Organization } from 'src/app/models/api/organization.model';
import { Role } from 'src/app/models/api/role.model';
import { User } from 'src/app/models/api/user.model';
import { PASSWORD_VALIDATORS } from 'src/app/validators/passwordValidators';
import { OrganizationService } from 'src/app/services/organization.service';
import { createCompareValidator } from 'src/app/validators/compare.validator';
import { RuleService } from 'src/app/services/rule.service';
import { OperationType, ResourceType, Rule, Rule_ } from 'src/app/models/api/rule.model';
import { RoleService } from 'src/app/services/role.service';
import { BaseFormComponent } from '../../admin-base/base-form/base-form.component';
import { PermissionService } from 'src/app/services/permission.service';
import { NgIf, NgFor } from '@angular/common';
import { MatFormField, MatLabel, MatError, MatHint } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatSelect } from '@angular/material/select';
import { MatOption } from '@angular/material/core';
import { PermissionsMatrixServerComponent } from '../../permissions-matrix/server/permissions-matrix-server.component';
import { AlertComponent } from '../../alerts/alert/alert.component';
import { MatButton } from '@angular/material/button';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { MatCheckbox } from '@angular/material/checkbox';

@Component({
  selector: 'app-user-form',
  templateUrl: './user-form.component.html',
  styleUrls: ['./user-form.component.scss'],
  imports: [
    NgIf,
    ReactiveFormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatError,
    MatSelect,
    NgFor,
    MatOption,
    MatCheckbox,
    MatHint,
    PermissionsMatrixServerComponent,
    AlertComponent,
    MatButton,
    MatProgressSpinner,
    TranslateModule
  ]
})
export class UserFormComponent extends BaseFormComponent implements OnInit, OnDestroy {
  @Input() user?: User;
  organizations: (BaseOrganization | Organization)[] = [];

  form = this.fb.nonNullable.group(
    {
      username: ['', [Validators.required]],
      email: ['', [Validators.required]],
      create_in_keycloak: [true],
      password: ['', [Validators.required, ...PASSWORD_VALIDATORS]],
      passwordRepeat: ['', [Validators.required]],
      firstname: '',
      lastname: '',
      organization_id: [NaN as number, [Validators.required]],
      roles: [{ value: [] as number[], disabled: true }],
      rules: [{ value: [] as number[], disabled: true }]
    },
    {
      validators: [createCompareValidator('password', 'passwordRepeat')]
    }
  );

  organizationRoles: Role[] = [];
  isEditOwnUser: boolean = false;
  /* Roles assigned to the user, prior to editing. */
  userRoles: Role[] = [];
  /* The rules that belong to the selected roles */
  roleRules: Rule[] = [];
  /* The selected rules that are specific to this user, prior to editing */
  userRules: Rule[] = [];
  /* The selected rules that are specific to this user, during editing */
  editSessionUserRules: Rule[] = [];
  /* The rules that the current user (probably an admin) is allowed to select/deselect. */
  selectableRules: Rule[] = [];

  constructor(
    private fb: FormBuilder,
    private organizationService: OrganizationService,
    private ruleService: RuleService,
    private roleService: RoleService,
    private permissionService: PermissionService
  ) {
    super();
  }

  async ngOnInit(): Promise<void> {
    this.isLoading = true;

    this.isEdit = !!this.user;
    this.setPermissions();

    // initialize validators for password and passwordRepeat and update them when
    // create_in_keycloak changes
    this.togglePasswordValidators(this.form.controls.create_in_keycloak.value);
    this.form.controls.create_in_keycloak.valueChanges.pipe(takeUntil(this.destroy$)).subscribe((createInKeycloak) => {
      this.togglePasswordValidators(createInKeycloak);
    });

    await this.initData();
    if (this.isEdit && this.user) {
      this.form.controls.username.setValue(this.user.username);
      this.form.controls.email.setValue(this.user.email);
      this.form.controls.firstname.setValue(this.user.firstname);
      this.form.controls.lastname.setValue(this.user.lastname);
      this.form.controls.organization_id.setValue(this.user.organization?.id || NaN);
      this.form.controls.roles.setValue(this.userRoles.map((role) => role.id));
    }
    this.setupForm();
    if (this.isEdit) {
      await this.getRoles(this.form.controls.organization_id.value);
    }

    this.isLoading = false;
  }

  private togglePasswordValidators(createInKeycloak: boolean): void {
    if (createInKeycloak) {
      this.form.controls.password.enable();
      this.form.controls.passwordRepeat.enable();
    } else {
      this.form.controls.password.disable();
      this.form.controls.passwordRepeat.disable();
    }
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

    this.form.controls.roles.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (roleIds) => {
      this.processRules(roleIds, this.editSessionUserRules);
    });
  }

  /**
   * 1. Get the rules of the currently selected roles.
   * 2. Get the selected rules that are specific to the selected user.
   *  */
  private async processRules(roleIds: number[], allUserRules: Rule[]): Promise<void> {
    this.roleRules = await this.ruleService.getRulesOfRoles(roleIds);
    this.editSessionUserRules = this.determineUserRules(this.roleRules, allUserRules);
  }

  private async initData(): Promise<void> {
    if (!this.isEdit) {
      // we only need to collect organizations when creating a new user
      this.organizations = await this.organizationService.getAllowedOrganizations(ResourceType.USER, OperationType.CREATE);
    }
    // TODO these should depend on the logged-in user's permissions
    this.selectableRules = await this.ruleService.getRules();

    // if creating new user, we don't need to get the roles of the user
    if (!this.user) return;

    this.userRoles = await this.roleService.getRoles({ user_id: this.user.id });
    const roleIds = this.userRoles.map((role) => role.id) ?? [];
    const userRules = await this.ruleService.getRules({ user_id: this.user.id });
    this.processRules(roleIds, userRules);
  }

  private async getRoles(organizationID: number): Promise<void> {
    this.organizationRoles = await this.organizationService.getRolesForOrganization(organizationID.toString());
    this.form.controls.roles.enable();
  }

  public handleChangedRules(rules: Rule_[]): void {
    this.editSessionUserRules = rules as Rule[];
    this.form.controls.rules.setValue(rules.map((rule) => rule.id));
  }

  override handleSubmit() {
    if (!this.form.valid) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const formValue: any = this.form.getRawValue();
    if (this.isEditOwnUser) {
      // remove roles and rules to prevent error that you are not allowed to edit your own roles and rules
      delete formValue.roles;
      delete formValue.rules;
    }
    this.submitted.emit(formValue);
  }

  /* Determine the set of selected rules that has no overlap with role rules. */
  private determineUserRules(roleRules: Rule[], userSelectedRules: Rule[]): Rule[] {
    if (!roleRules || !userSelectedRules) return [];
    return userSelectedRules.filter((userRule) => !roleRules.some((roleRule) => roleRule.id === userRule.id));
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.isEditOwnUser = this.isEdit && this.user?.id === this.permissionService.activeUser?.id;
        }
      });
  }
}
