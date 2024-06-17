import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { takeUntil } from 'rxjs';
import { PageEvent } from '@angular/material/paginator';
import { BaseUserListComponent } from 'src/app/components/admin-base/base-user-list/base-user-list.component';
import { unlikeApiParameter } from 'src/app/helpers/general.helper';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { StoreUser, getStoreUserParameters } from 'src/app/models/api/store-user.model';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { StoreUserService } from 'src/app/services/store-user.service';

@Component({
  selector: 'app-store-user-list',
  templateUrl: './store-user-list.component.html',
  styleUrl: './store-user-list.component.scss'
})
export class StoreUserListComponent extends BaseUserListComponent implements OnInit, OnDestroy {
  getUserParameters: getStoreUserParameters = {};

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private storeUserService: StoreUserService,
    private chosenStoreService: ChosenStoreService,
    private storePermissionService: StorePermissionService
  ) {
    super();
  }
  async handlePageEvent(e: PageEvent) {
    await this.getUsers(e.pageIndex + 1, this.getUserParameters);
  }

  handleTableClick(id: string) {
    this.router.navigate([this.routes.storeUser, id]);
  }

  async ngOnInit(): Promise<void> {
    this.storePermissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isInitialized) => {
        if (isInitialized) {
          this.canCreate = this.storePermissionService.isAllowed(StoreResourceType.USER, OperationType.CREATE);
          this.initData(this.currentPage, this.getUserParameters);
        }
      });
  }

  protected async initData(page: number, parameters: getStoreUserParameters) {
    this.isLoading = true;
    this.currentPage = page;
    this.getUserParameters = parameters;
    await this.getUsers(page, parameters);
    this.isLoading = false;
  }

  private async getUsers(page: number, getUserParameters: getStoreUserParameters) {
    const store = this.chosenStoreService.store$.value;
    if (!store) return;
    const result = await this.storeUserService.getPaginatedUsers(store.url, page, getUserParameters);
    this.table = {
      columns: [
        { id: 'id', label: this.translateService.instant('general.id') },
        {
          id: 'username',
          label: this.translateService.instant('user.username'),
          searchEnabled: true,
          initSearchString: unlikeApiParameter(getUserParameters.username)
        },
        { id: 'server', label: this.translateService.instant('store.server') }
      ],
      rows: result.data.map((user: StoreUser) => ({
        id: user.id.toString(),
        columnData: {
          id: user.id,
          username: user.username,
          server: user.server.url
        }
      }))
    };
    this.pagination = result.links;
  }
}
