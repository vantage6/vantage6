import { Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-organization-list',
  templateUrl: './organization-list.component.html',
  styleUrls: ['./organization-list.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class OrganizationListComponent implements OnInit {
  routes = routePaths;

  isLoading: boolean = true;
  canCreate: boolean = false;
  table?: TableData;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private organizationService: OrganizationService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.canCreate = this.authService.isOperationAllowed(ScopeType.GLOBAL, ResourceType.ORGANIZATION, OperationType.CREATE);
    this.initData();
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getOrganizations();
  }

  handleTableClick(id: string): void {
    this.router.navigate([routePaths.organization, id]);
  }

  private async initData() {
    await this.getOrganizations();
    this.isLoading = false;
  }

  private async getOrganizations() {
    const result = await this.organizationService.getPaginatedOrganizations(this.currentPage, { sort: OrganizationSortProperties.Name });

    this.table = {
      columns: [
        { id: 'name', label: this.translateService.instant('organization.name') },
        { id: 'country', label: this.translateService.instant('organization.country') }
      ],
      rows: result.data.map((_) => ({ id: _.id.toString(), columnData: { name: _.name, country: _.country } }))
    };
    this.pagination = result.links;
  }
}
