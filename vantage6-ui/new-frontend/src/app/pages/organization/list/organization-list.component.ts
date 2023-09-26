import { Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { OrganizationService } from 'src/app/services/organization.service';

enum TableRows {
  Name = 'name'
}

@Component({
  selector: 'app-organization-list',
  templateUrl: './organization-list.component.html',
  styleUrls: ['./organization-list.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class OrganizationListComponent implements OnInit {
  routes = routePaths;
  tableRows = TableRows;

  isLoading: boolean = true;
  canCreate: boolean = false;
  organizations: BaseOrganization[] = [];
  displayedColumns: string[] = [TableRows.Name];
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;

  constructor(
    private router: Router,
    private organizationService: OrganizationService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.canCreate = this.authService.isOperationAllowed(ScopeType.GLOBAL, ResourceType.ORGANIZATION, OperationType.CREATE);
    this.initData();
  }

  handleRowClick(organization: BaseOrganization) {
    this.router.navigate([routePaths.organization, organization.id]);
  }

  handleRowKeyPress(event: KeyboardEvent, organization: BaseOrganization) {
    if (event.key === 'Enter' || event.key === ' ') {
      this.handleRowClick(organization);
    }
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getOrganizations();
  }

  private async initData() {
    await this.getOrganizations();
    this.isLoading = false;
  }

  private async getOrganizations() {
    const result = await this.organizationService.getPaginatedOrganizations(this.currentPage);
    this.organizations = result.data;
    this.pagination = result.links;
  }
}
