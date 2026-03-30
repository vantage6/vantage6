import { Component, OnInit } from '@angular/core';
import { PageEvent, MatPaginator } from '@angular/material/paginator';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { takeUntil } from 'rxjs';
import { BaseListComponent } from 'src/app/components/admin-base/base-list/base-list.component';
import { unlikeApiParameter } from 'src/app/helpers/general.helper';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { GetStoreRoleParameters, StoreRole } from 'src/app/models/api/store-role.model';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { StoreRoleService } from 'src/app/services/store-role.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatCard, MatCardContent } from '@angular/material/card';
import { TableComponent } from '../../../../components/table/table.component';

@Component({
  selector: 'app-store-role-list',
  templateUrl: './store-role-list.component.html',
  styleUrl: './store-role-list.component.scss',
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
export class StoreRoleListComponent extends BaseListComponent implements OnInit {
  getRoleParameters: GetStoreRoleParameters = {};

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private storeRoleService: StoreRoleService,
    private chosenStoreService: ChosenStoreService,
    private storePermissionService: StorePermissionService
  ) {
    super();
  }

  async ngOnInit(): Promise<void> {
    this.storePermissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isInitialized) => {
        if (isInitialized) {
          this.canCreate = this.storePermissionService.isAllowed(StoreResourceType.ROLE, OperationType.CREATE);
          this.initData(this.currentPage, this.getRoleParameters);
        }
      });
  }

  async handlePageEvent(e: PageEvent) {
    await this.getRoles(e.pageIndex + 1, this.getRoleParameters);
  }

  handleTableClick(id: string) {
    this.router.navigate([this.routes.storeRole, id]);
  }

  protected async initData(page: number, parameters: GetStoreRoleParameters) {
    this.isLoading = true;
    this.currentPage = page;
    this.getRoleParameters = parameters;
    await this.getRoles(page, parameters);
    this.isLoading = false;
  }

  private async getRoles(page: number, getRoleParameters: GetStoreRoleParameters) {
    const store = this.chosenStoreService.store$.value;
    if (!store) return;
    const result = await this.storeRoleService.getPaginatedRoles(store, page, getRoleParameters);
    this.table = {
      columns: [
        { id: 'id', label: this.translateService.instant('general.id') },
        {
          id: 'name',
          label: this.translateService.instant('general.name'),
          searchEnabled: true,
          initSearchString: unlikeApiParameter(getRoleParameters.name)
        }
      ],
      rows: result.data.map((role: StoreRole) => ({
        id: role.id.toString(),
        columnData: {
          id: role.id,
          name: role.name
        }
      }))
    };
    this.pagination = result.links;
  }
}
