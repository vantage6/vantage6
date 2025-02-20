import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { takeUntil } from 'rxjs';
import { BaseReadComponent } from 'src/app/components/admin-base/base-read/base-read.component';
import { OperationType, StoreResourceType, StoreRule } from 'src/app/models/api/rule.model';
import { StoreUser, StoreUserLazyProperties } from 'src/app/models/api/store-user.model';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { HandleConfirmDialogService } from 'src/app/services/handle-confirm-dialog.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { StoreRuleService } from 'src/app/services/store-rule.service';
import { StoreUserService } from 'src/app/services/store-user.service';
import { NgIf, NgFor } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatIconButton } from '@angular/material/button';
import { MatMenuTrigger, MatMenu, MatMenuItem } from '@angular/material/menu';
import { MatIcon } from '@angular/material/icon';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { ChipComponent } from '../../../../components/helpers/chip/chip.component';
import { PermissionsMatrixStoreComponent } from '../../../../components/permissions-matrix/store/permissions-matrix-store.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
    selector: 'app-store-user-read',
    templateUrl: './store-user-read.component.html',
    styleUrl: './store-user-read.component.scss',
    imports: [
        NgIf,
        PageHeaderComponent,
        MatIconButton,
        MatMenuTrigger,
        MatIcon,
        MatMenu,
        MatMenuItem,
        RouterLink,
        MatCard,
        MatCardHeader,
        MatCardTitle,
        MatCardContent,
        NgFor,
        ChipComponent,
        PermissionsMatrixStoreComponent,
        MatProgressSpinner,
        TranslateModule
    ]
})
export class StoreUserReadComponent extends BaseReadComponent implements OnInit, OnDestroy {
  user: StoreUser | null = null;
  allUserRules: StoreRule[] = [];
  StoreResourceType = StoreResourceType;

  constructor(
    protected override handleConfirmDialogService: HandleConfirmDialogService,
    protected override translateService: TranslateService,
    private router: Router,
    private storeUserService: StoreUserService,
    private chosenStoreService: ChosenStoreService,
    private storePermissionService: StorePermissionService,
    private storeRuleService: StoreRuleService
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
    this.user = await this.storeUserService.getUser(store?.url, this.id, [StoreUserLazyProperties.Roles]);

    this.setPermissions();
    this.allUserRules = await this.storeRuleService.getRules(store.url, { username: this.user.username, server_url: this.user.server.url });

    this.isLoading = false;
  }

  private setPermissions(): void {
    this.canDelete = this.storePermissionService.isAllowed(StoreResourceType.USER, OperationType.DELETE);
    this.canEdit = this.storePermissionService.isAllowed(StoreResourceType.USER, OperationType.EDIT);
  }

  async handleDelete(): Promise<void> {
    this.handleDeleteBase(
      this.user,
      this.translateService.instant('store-user.delete-dialog.title', {
        name: this.user?.username,
        store_name: this.chosenStoreService.store$.value?.name || ''
      }),
      this.translateService.instant('store-user.delete-dialog.content', { username: this.user?.username }),
      async () => {
        const store = this.chosenStoreService.store$.value;
        if (!store || !this.user) return;
        this.isLoading = true;
        await this.storeUserService.deleteUser(store.url, this.user.id);
        this.router.navigate([this.routes.storeUsers]);
      }
    );
  }
}
