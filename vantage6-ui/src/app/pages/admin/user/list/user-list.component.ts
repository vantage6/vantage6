import { Component, OnDestroy, OnInit } from '@angular/core';
import { PageEvent, MatPaginator } from '@angular/material/paginator';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { takeUntil } from 'rxjs';
import { BaseListComponent } from 'src/app/components/admin-base/base-list/base-list.component';
import {
  ITreeInputNode,
  ITreeSelectedValue,
  TreeDropdownComponent
} from 'src/app/components/helpers/tree-dropdown/tree-dropdown.component';
import { unlikeApiParameter } from 'src/app/helpers/general.helper';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { GetUserParameters, UserSortProperties } from 'src/app/models/api/user.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { PermissionService } from 'src/app/services/permission.service';
import { UserService } from 'src/app/services/user.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatCard, MatCardContent } from '@angular/material/card';
import { TableComponent } from '../../../../components/table/table.component';

@Component({
  selector: 'app-user-list',
  templateUrl: './user-list.component.html',
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
    TranslateModule,
    TreeDropdownComponent
  ]
})
export class UserListComponent extends BaseListComponent implements OnInit, OnDestroy {
  getUserParameters: GetUserParameters = {};

  filterOptions: ITreeInputNode[] = [];
  selectedFilterOptions: ITreeSelectedValue[] = [];

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private userService: UserService,
    private organizationService: OrganizationService,
    private permissionService: PermissionService
  ) {
    super();
  }

  async ngOnInit(): Promise<void> {
    this.setPermissions();
    await this.initData(this.currentPage, this.getUserParameters);
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getUsers();
  }

  handleTableClick(id: string) {
    this.router.navigate([this.routes.user, id]);
  }

  async handleFilterSelectionChange(newSelected: ITreeSelectedValue[]): Promise<void> {
    // Tree-dropdown component supports multiselect, but the API call for retrieving paginated nodes does not (yet) support multiple filter parameters. For now, the first value is selected.
    this.selectedFilterOptions = newSelected.length ? [newSelected[0]] : [];
    await this.getUsers(newSelected[0]);
  }

  getFilterPlaceholder(): string {
    return this.translateService.instant('user-list.filter-placeholder');
  }

  protected async initData(page: number, parameters: GetUserParameters) {
    this.isLoading = true;
    this.currentPage = page;
    this.getUserParameters = parameters;
    await this.getUsers();
    await this.getFilterOptions();
    this.isLoading = false;
  }

  private async getUsers(selectedFilterOption: ITreeSelectedValue | null = null) {
    const getUserParameters = { ...this.getUserParameters };
    if (selectedFilterOption) {
      getUserParameters.organization_id = selectedFilterOption.code.toString();
    }
    const result = await this.userService.getPaginatedUsers(this.currentPage, { ...getUserParameters, sort: UserSortProperties.Username });
    this.table = {
      columns: [
        { id: 'id', label: this.translateService.instant('general.id') },
        {
          id: 'username',
          label: this.translateService.instant('user.username'),
          searchEnabled: true,
          initSearchString: unlikeApiParameter(this.getUserParameters.username)
        }
      ],
      rows: result.data.map((_) => ({
        id: _.id.toString(),
        columnData: { id: _.id, username: _.username }
      }))
    };
    this.pagination = result.links;
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canCreate = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.USER, OperationType.CREATE);
        }
      });
  }

  private async getFilterOptions() {
    const organizations = await this.organizationService.getOrganizations();

    this.filterOptions = organizations.map((organization) => {
      return {
        isFolder: false,
        children: [],
        label: organization.name,
        code: organization.id,
        parentCode: this.translateService.instant('resources.organization').toLowerCase()
      };
    });
  }
}
