import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { takeUntil } from 'rxjs';
import { BaseReadComponent } from 'src/app/components/admin-base/base-read/base-read.component';
import { Organization } from 'src/app/models/api/organization.model';
import { Role, RoleLazyProperties } from 'src/app/models/api/role.model';
import { OperationType, ResourceType, Rule, Rule_ } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { HandleConfirmDialogService } from 'src/app/services/handle-confirm-dialog.service';
import { OrganizationService } from 'src/app/services/organization.service';
import { PermissionService } from 'src/app/services/permission.service';
import { RoleService } from 'src/app/services/role.service';
import { RuleService } from 'src/app/services/rule.service';
import { NgIf } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatTabGroup, MatTab } from '@angular/material/tabs';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { PermissionsMatrixServerComponent } from '../../../../components/permissions-matrix/server/permissions-matrix-server.component';
import { RoleSubmitButtonsComponent } from '../../../../components/helpers/role-submit-buttons/role-submit-buttons.component';
import { TableComponent } from '../../../../components/table/table.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
    selector: 'app-role-read',
    templateUrl: './role-read.component.html',
    styleUrls: ['./role-read.component.scss'],
    imports: [
        NgIf,
        PageHeaderComponent,
        MatCard,
        MatCardContent,
        MatTabGroup,
        MatTab,
        MatButton,
        MatIcon,
        PermissionsMatrixServerComponent,
        RoleSubmitButtonsComponent,
        TableComponent,
        MatProgressSpinner,
        TranslateModule
    ]
})
export class RoleReadComponent extends BaseReadComponent implements OnInit, OnDestroy {
  isEditing: boolean = false;

  role: Role | null = null;
  roleRules: Rule[] = [];
  roleOrganization?: Organization;
  allRules: Rule[] = [];
  userTable?: TableData;

  /* Bound variables to permission matrix. */
  preselectedRules: Rule[] = [];
  selectableRules: Rule[] = [];
  fixedSelectedRules: Rule[] = [];

  changedRules?: Rule[];
  errorMessage?: string;

  constructor(
    protected override handleConfirmDialogService: HandleConfirmDialogService,
    private router: Router,
    private roleService: RoleService,
    private ruleService: RuleService,
    private organizationService: OrganizationService,
    protected override translateService: TranslateService,
    private permissionService: PermissionService
  ) {
    super(handleConfirmDialogService, translateService);
  }

  override async ngOnInit(): Promise<void> {
    this.allRules = await this.ruleService.getRules();
    try {
      await this.initData();
    } catch (error) {
      this.handleHttpError(error as HttpErrorResponse);
      this.isLoading = false;
    }
  }

  private handleHttpError(error: HttpErrorResponse): void {
    this.errorMessage = error.error['msg'] ?? error.message;
  }

  protected async initData(): Promise<void> {
    this.role = await this.roleService.getRole(this.id, [RoleLazyProperties.Users]);
    this.setPermissions();
    const organizationId = this.role.organization?.id.toString();
    if (organizationId) {
      this.roleOrganization = await this.organizationService.getOrganization(organizationId as string);
    }
    this.userTable = {
      columns: [
        { id: 'username', label: this.translateService.instant('user.username') },
        { id: 'firstname', label: this.translateService.instant('user.first-name') },
        { id: 'lastname', label: this.translateService.instant('user.last-name') },
        { id: 'email', label: this.translateService.instant('user.email') }
      ],
      rows: this.role.users.map((user) => ({
        id: user.id.toString(),
        columnData: { ...user }
      }))
    };
    this.roleRules = await this.ruleService.getRules({ role_id: this.id });
    this.enterEditMode(false);
    this.isLoading = false;
  }

  private enterEditMode(edit: boolean): void {
    this.isEditing = edit;
    if (edit) {
      this.preselectedRules = this.roleRules;
      this.fixedSelectedRules = [];
      this.selectableRules = this.allRules;
    } else {
      this.preselectedRules = [];
      this.fixedSelectedRules = this.roleRules;
      this.selectableRules = this.roleRules;
    }
  }

  public handleDeleteRole(): void {
    this.handleDeleteBase(
      this.role,
      this.translateService.instant('role-read.delete-dialog.title', { name: this.role?.name }),
      this.translateService.instant('role-read.delete-dialog.content'),
      async () => {
        if (!this.role) return;
        this.isLoading = true;
        await this.roleService.deleteRole(this.role.id);
        this.router.navigate([routePaths.roles]);
      }
    );
  }

  public handleEnterEditMode(): void {
    this.enterEditMode(true);
  }

  public handleCancelEdit(): void {
    this.enterEditMode(false);
  }

  public get showData(): boolean {
    return !this.isLoading && this.role != undefined;
  }

  public get showUserTable(): boolean {
    return this.userTable != undefined && this.userTable.rows.length > 0;
  }

  public handleChangedSelection(rules: Rule_[]): void {
    this.changedRules = rules as Rule[];
  }

  // TODO: handle error
  public async handleSubmitEdit(): Promise<void> {
    if (!this.role || !this.changedRules) return;

    this.isLoading = true;
    const role: Role = { ...this.role, rules: this.changedRules };
    await this.roleService.patchRole(role);
    this.changedRules = [];
    this.initData();
  }

  public get editEnabled(): boolean {
    return this.canEdit && !this.role?.is_default_role;
  }

  public get deleteEnabled(): boolean {
    return this.canDelete && !this.role?.is_default_role;
  }

  public get submitDisabled(): boolean {
    return this.changedRules?.length === 0;
  }

  getDefaultRoleLabel(): string {
    if (!this.role) return '';
    return this.role.is_default_role ? this.translateService.instant('general.yes') : this.translateService.instant('general.no');
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized && this.role) {
          this.canEdit = this.permissionService.isAllowedForOrg(ResourceType.ROLE, OperationType.EDIT, this.role.organization?.id || null);
          this.canDelete = this.permissionService.isAllowedForOrg(
            ResourceType.ROLE,
            OperationType.DELETE,
            this.role.organization?.id || null
          );
        }
      });
  }
}
