import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { takeUntil } from 'rxjs';
import { BaseReadComponent } from 'src/app/components/admin-base/base-read/base-read.component';
import { OperationType, StoreResourceType, StoreRule } from 'src/app/models/api/rule.model';
import { StoreRole, StoreRoleLazyProperties } from 'src/app/models/api/store-role.model';
import { TableData } from 'src/app/models/application/table.model';
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
        TranslateModule
    ]
})
export class StoreRoleReadComponent extends BaseReadComponent implements OnInit, OnDestroy {
  isEditing: boolean = false;
  role: StoreRole | null = null;
  roleRules: StoreRule[] = [];
  userTable?: TableData;

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
          this.initData();
        }
      });
  }

  protected async initData(): Promise<void> {
    const store = this.chosenStoreService.store$.value;
    if (!store) return;
    this.role = await this.storeRoleService.getRole(store?.url, this.id, [StoreRoleLazyProperties.Users]);
    this.roleRules = await this.storeRuleService.getRules(store?.url, { role_id: this.id });
    this.setPermissions();
    this.setUpUserTable();

    this.isLoading = false;
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
}
