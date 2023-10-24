import { Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { CollaborationSortProperties } from 'src/app/models/api/collaboration.model';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';

@Component({
  selector: 'app-collaboration-list',
  templateUrl: './collaboration-list.component.html',
  styleUrls: ['./collaboration-list.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class CollaborationListComponent implements OnInit {
  routes = routePaths;

  isLoading: boolean = true;
  canCreate: boolean = false;
  table?: TableData;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private collaborationService: CollaborationService,
    private permissionService: PermissionService
  ) {}

  ngOnInit(): void {
    this.canCreate = this.permissionService.isAllowed(ScopeType.GLOBAL, ResourceType.COLLABORATION, OperationType.CREATE);
    this.initData();
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getCollaborations();
  }

  handleTableClick(id: string): void {
    this.router.navigate([routePaths.collaboration, id]);
  }

  private async initData() {
    await this.getCollaborations();
    this.isLoading = false;
  }

  private async getCollaborations() {
    const result = await this.collaborationService.getPaginatedCollaborations(this.currentPage, { sort: CollaborationSortProperties.Name });

    this.table = {
      columns: [
        { id: 'name', label: this.translateService.instant('collaboration.name') },
        { id: 'encrypted', label: this.translateService.instant('collaboration.encrypted') }
      ],
      rows: result.data.map((_) => ({
        id: _.id.toString(),
        columnData: {
          name: _.name,
          encrypted: _.encrypted ? this.translateService.instant('general.yes') : this.translateService.instant('general.no')
        }
      }))
    };
    this.pagination = result.links;
  }
}
