import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { takeUntil } from 'rxjs';
import { PageEvent, MatPaginator } from '@angular/material/paginator';
import { BaseListComponent } from 'src/app/components/admin-base/base-list/base-list.component';
import { unlikeApiParameter } from 'src/app/helpers/general.helper';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { StoreUser, GetStoreUserParameters } from 'src/app/models/api/store-user.model';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { StoreUserService } from 'src/app/services/store-user.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatCard, MatCardContent } from '@angular/material/card';
import { TableComponent } from '../../../../components/table/table.component';

@Component({
  selector: 'app-store-user-list',
  templateUrl: './store-user-list.component.html',
  styleUrl: './store-user-list.component.scss',
  imports: [
    PageHeaderComponent,
    NgIf,
    MatButton,
    RouterLink,
    MatIcon,
    MatCard,
    MatCardContent,
    TableComponent,
    MatPaginator,
    TranslateModule
  ]
})
export class StoreUserListComponent extends BaseListComponent implements OnInit, OnDestroy {
  getUserParameters: GetStoreUserParameters = {};

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

  protected async initData(page: number, parameters: GetStoreUserParameters) {
    this.isLoading = true;
    this.currentPage = page;
    this.getUserParameters = parameters;
    await this.getUsers(page, parameters);
    this.isLoading = false;
  }

  private async getUsers(page: number, getUserParameters: GetStoreUserParameters) {
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
        }
      ],
      rows: result.data.map((user: StoreUser) => ({
        id: user.id.toString(),
        columnData: {
          id: user.id,
          username: user.username
        }
      }))
    };
    this.pagination = result.links;
  }
}
