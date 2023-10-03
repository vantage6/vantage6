import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { BaseUser, UserSortProperties } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { UserService } from 'src/app/services/user.service';

enum TableRows {
  Username = 'username',
  Email = 'email',
  FirstName = 'firstName',
  LastName = 'lastName'
}

@Component({
  selector: 'app-user-list',
  templateUrl: './user-list.component.html',
  styleUrls: ['./user-list.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class UserListComponent implements OnInit, OnDestroy {
  destroy$ = new Subject();
  tableRows = TableRows;
  routes = routePaths;

  isLoading: boolean = true;
  canCreate: boolean = false;
  displayedColumns: string[] = [];
  users: BaseUser[] = [];
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;

  constructor(
    private router: Router,
    private userService: UserService,
    private authService: AuthService,
    private breakpointObserver: BreakpointObserver
  ) {}

  ngOnInit(): void {
    this.breakpointObserver.observe([Breakpoints.Medium, Breakpoints.Large, Breakpoints.XLarge]).subscribe((result) => {
      if (result.matches) {
        this.displayedColumns = [TableRows.Username, TableRows.FirstName, TableRows.LastName, TableRows.Email];
      } else {
        this.displayedColumns = [TableRows.Username, TableRows.FirstName, TableRows.LastName];
      }
    });
    this.canCreate = this.authService.isOperationAllowed(ScopeType.ANY, ResourceType.USER, OperationType.CREATE);
    this.initData();
  }

  ngOnDestroy() {
    this.destroy$.next(true);
  }

  handleRowClick(user: BaseUser) {
    this.router.navigate([routePaths.user, user.id]);
  }

  handleRowKeyPress(event: KeyboardEvent, user: BaseUser) {
    if (event.key === 'Enter' || event.key === ' ') {
      this.handleRowClick(user);
    }
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getUsers();
  }

  private async initData() {
    await this.getUsers();
    this.isLoading = false;
  }

  private async getUsers() {
    const result = await this.userService.getPaginatedUsers(this.currentPage, { sort: UserSortProperties.Username });
    this.users = result.data;
    this.pagination = result.links;
  }
}
