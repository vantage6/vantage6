import { Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { BaseCollaboration, CollaborationSortProperties } from 'src/app/models/api/collaboration.model';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { CollaborationService } from 'src/app/services/collaboration.service';

enum TableRows {
  Name = 'name'
}

@Component({
  selector: 'app-collaboration-list',
  templateUrl: './collaboration-list.component.html',
  styleUrls: ['./collaboration-list.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class CollaborationListComponent implements OnInit {
  tableRows = TableRows;
  routes = routePaths;

  isLoading: boolean = true;
  canCreate: boolean = false;
  displayedColumns: string[] = [TableRows.Name];
  collaborations: BaseCollaboration[] = [];
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;

  constructor(
    private router: Router,
    private collaborationService: CollaborationService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.canCreate = this.authService.isOperationAllowed(ScopeType.GLOBAL, ResourceType.COLLABORATION, OperationType.CREATE);
    this.initData();
  }

  handleRowClick(collaboration: BaseCollaboration) {
    this.router.navigate([routePaths.collaboration, collaboration.id]);
  }

  handleRowKeyPress(event: KeyboardEvent, collaboration: BaseCollaboration) {
    if (event.key === 'Enter' || event.key === ' ') {
      this.handleRowClick(collaboration);
    }
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getCollaborations();
  }

  private async initData() {
    await this.getCollaborations();
    this.isLoading = false;
  }

  private async getCollaborations() {
    const result = await this.collaborationService.getPaginatedCollaborations(this.currentPage, CollaborationSortProperties.Name);
    this.collaborations = result.data;
    this.pagination = result.links;
  }
}
