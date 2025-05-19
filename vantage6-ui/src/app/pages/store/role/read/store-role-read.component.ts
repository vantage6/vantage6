import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { takeUntil } from 'rxjs';
import { BaseReadComponent } from 'src/app/components/admin-base/base-read/base-read.component';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { OperationType, Rule_, StoreResourceType, StoreRule } from 'src/app/models/api/rule.model';
import { StoreRole, StoreRoleLazyProperties } from 'src/app/models/api/store-role.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { HandleConfirmDialogService } from 'src/app/services/handle-confirm-dialog.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { StoreRoleService } from 'src/app/services/store-role.service';
import { StoreRuleService } from 'src/app/services/store-rule.service';
import { NgIf } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatTabGroup, MatTab } from '@angular/material/tabs';
import { PermissionsMatrixStoreComponent } from '../../../../components/permissions-matrix/store/permissions-matrix-store.component';
import { TableComponent } from '../../../../components/table/table.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { RoleSubmitButtonsComponent } from 'src/app/components/helpers/role-submit-buttons/role-submit-buttons.component';
import { MatIcon } from '@angular/material/icon';

@Component({
  selector: 'app-store-role-read',
  templateUrl: './store-role-read.component.html',
  styleUrl: './store-role-read.component.scss',
  imports: [
    NgIf,
    PageHeaderComponent,
    MatCard,
    MatCardContent,
    MatTabGroup,
    MatTab,
    PermissionsMatrixStoreComponent,
    TableComponent,
    MatProgressSpinner,
    TranslateModule,
    RoleSubmitButtonsComponent,
    MatIcon
  ]
})
export class StoreRoleReadComponent extends BaseReadComponent implements OnInit, OnDestroy {
  isEditing: boolean = false;
  role: StoreRole | null = null;
  roleRules: StoreRule[] = [];
  allRules: StoreRule[] = [];
  userTable?: TableData;

  /* Bound variables to permission matrix. */
  preselectedRules: StoreRule[] = [];
  selectableRules: StoreRule[] = [];
  fixedSelectedRules: StoreRule[] = [];

  changedRules?: StoreRule[];
  store: AlgorithmStore | null = null;

  constructor(
    protected override handleConfirmDialogService: HandleConfirmDialogService,
    private router: Router,
    private storeRoleService: StoreRoleService,
    private storeRuleService: StoreRuleService,
    protected override translateService: TranslateService,
    private storePermissionService: StorePermissionService,
    private chosenStoreService: ChosenStoreService
  ) {
    super(handleConfirmDialogService, translateService);
  }

  override async ngOnInit(): Promise<void> {
    this.storePermissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isInitialized) => {
        if (isInitialized) {
          this.store = this.chosenStoreService.store$.value;
          this.initData();
        }
      });
  }

  protected async initData(): Promise<void> {
    if (!this.store) return;
    this.role = await this.storeRoleService.getRole(this.store?.url, this.id, [StoreRoleLazyProperties.Users]);
    this.allRules = await this.storeRuleService.getRules(this.store?.url);
    this.roleRules = await this.storeRuleService.getRules(this.store?.url, { role_id: this.id });
    this.setPermissions();
    this.setUpUserTable();
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
        if (!this.store) return;
        this.isLoading = true;
        await this.storeRoleService.deleteRole(this.store?.url, this.role.id);
        this.router.navigate([routePaths.storeRoles]);
      }
    );
  }

  public handleEnterEditMode(): void {
    this.enterEditMode(true);
  }

  public handleCancelEdit(): void {
    this.enterEditMode(false);
  }

  private setPermissions(): void {
    this.canDelete = this.storePermissionService.isAllowed(StoreResourceType.ROLE, OperationType.DELETE);
    this.canEdit = this.storePermissionService.isAllowed(StoreResourceType.ROLE, OperationType.EDIT);
  }

  public get showData(): boolean {
    return !this.isLoading && this.role != undefined;
  }

  public get showUserTable(): boolean {
    return this.userTable != undefined && this.userTable.rows.length > 0;
  }

  public handleChangedSelection(rules: Rule_[]): void {
    this.changedRules = rules as StoreRule[];
  }

  public async handleSubmitEdit(): Promise<void> {
    if (!this.role || !this.changedRules) return;
    const store = this.chosenStoreService.store$.value;
    if (!store) return;
    this.isLoading = true;
    const role: StoreRole = { ...this.role, rules: this.changedRules };
    await this.storeRoleService.patchRole(store.url, role);
    this.changedRules = [];
    this.initData();
  }

  private setUpUserTable(): void {
    if (!this.role || !this.role.users) return;
    this.userTable = {
      columns: [
        { id: 'username', label: this.translateService.instant('user.username') },
        { id: 'serverurl', label: this.translateService.instant('store-user.server') }
      ],
      rows: this.role?.users?.map((user) => ({
        id: user.id.toString(),
        columnData: {
          username: user.username,
          serverurl: user.server.url
        }
      }))
    };
  }

  public get editEnabled(): boolean {
    return this.canEdit && !this.role?.is_default_role;
  }

  public get deleteEnabled(): boolean {
    return this.canDelete && !this.role?.is_default_role;
  }

  getDefaultRoleLabel(): string {
    if (!this.role) return '';
    return this.role.is_default_role ? this.translateService.instant('general.yes') : this.translateService.instant('general.no');
  }
}
