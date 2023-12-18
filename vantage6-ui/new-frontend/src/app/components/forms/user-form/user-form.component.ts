import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { BaseOrganization, OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { Role } from 'src/app/models/api/role.model';
import { User, UserForm } from 'src/app/models/api/user.model';
import { PASSWORD_VALIDATORS } from 'src/app/validators/passwordValidators';
import { OrganizationService } from 'src/app/services/organization.service';
import { createCompareValidator } from 'src/app/validators/compare.validator';
import { RuleService } from 'src/app/services/rule.service';
import { Rule } from 'src/app/models/api/rule.model';
import { RoleService } from 'src/app/services/role.service';

@Component({
  selector: 'app-user-form',
  templateUrl: './user-form.component.html',
  styleUrls: ['./user-form.component.scss']
})
export class UserFormComponent implements OnInit, OnDestroy {
  @Input() user?: User;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<UserForm> = new EventEmitter();

  destroy$ = new Subject();
  form = this.fb.nonNullable.group(
    {
      username: ['', [Validators.required]],
      email: ['', [Validators.required]],
      password: ['', [Validators.required, ...PASSWORD_VALIDATORS]],
      passwordRepeat: ['', [Validators.required]],
      firstname: '',
      lastname: '',
      organization_id: [NaN as number, [Validators.required]],
      roles: [{ value: [] as number[], disabled: true }, [Validators.required]],
      rules: [{ value: [] as number[], disabled: true }]
    },
    { validators: [createCompareValidator('password', 'passwordRepeat')] }
  );
  isEdit: boolean = false;
  isLoading: boolean = true;
  organizations: BaseOrganization[] = [];
  organizationRoles: Role[] = [];
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
    private roleService: RoleService
  ) {}

  async ngOnInit(): Promise<void> {
    this.isLoading = true;

    this.isEdit = !!this.user;
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

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  handleSubmit() {
    if (this.form.valid) {
      this.submitted.emit(this.form.getRawValue());
    }
  }

  handleCancel() {
    this.cancelled.emit();
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
    if (!this.user) return;

    if (!this.isEdit) {
      // we only need to collect organizations when creating a new user
      // TODO ensure that this goes well with pagination
      this.organizations = await this.organizationService.getOrganizations({ sort: OrganizationSortProperties.Name });
    }

    this.selectableRules = await this.ruleService.getAllRules();
    this.userRoles = await this.roleService.getRoles({ user_id: this.user.id, per_page: 1000 });
    const roleIds = this.userRoles.map((role) => role.id) ?? [];
    const userRules = await this.ruleService.getRules({ user_id: this.user.id, no_pagination: 1 });
    this.processRules(roleIds, userRules);
  }

  private async getRoles(organizationID: number): Promise<void> {
    this.organizationRoles = await this.organizationService.getRolesForOrganization(organizationID.toString());
    this.form.controls.roles.enable();
  }

  public handleChangedRules(rules: Rule[]): void {
    this.editSessionUserRules = rules;
    this.form.controls.rules.setValue(rules.map((rule) => rule.id));
  }

  /* Determine the set of selected rules that has no overlap with role rules. */
  private determineUserRules(roleRules: Rule[], userSelectedRules: Rule[]): Rule[] {
    if (!roleRules || !userSelectedRules) return [];
    return userSelectedRules.filter((userRule) => !roleRules.some((roleRule) => roleRule.id === userRule.id));
  }
}
