import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject } from 'rxjs';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { UserSortProperties } from 'src/app/models/api/user.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { UserService } from 'src/app/services/user.service';

@Component({
  selector: 'app-user-list',
  templateUrl: './user-list.component.html',
  styleUrls: ['./user-list.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class UserListComponent implements OnInit, OnDestroy {
  destroy$ = new Subject();
  routes = routePaths;

  isLoading: boolean = true;
  canCreate: boolean = false;
  table?: TableData;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private userService: UserService,
    private authService: AuthService,
    private breakpointObserver: BreakpointObserver
  ) {}

  ngOnInit(): void {
    //TODO: Implement responsive columns in table component
    this.breakpointObserver.observe([Breakpoints.Medium, Breakpoints.Large, Breakpoints.XLarge]).subscribe((result) => {
      if (!this.table) return;

      if (result.matches) {
        this.table = {
          ...this.table,
          columns: [
            { id: 'username', label: this.translateService.instant('user.username') },
            { id: 'firsname', label: this.translateService.instant('user.first-name') },
            { id: 'lastname', label: this.translateService.instant('user.last-name') },
            { id: 'email', label: this.translateService.instant('user.email') }
          ]
        };
      } else {
        this.table = {
          ...this.table,
          columns: [
            { id: 'username', label: this.translateService.instant('user.username') },
            { id: 'email', label: this.translateService.instant('user.email') }
          ]
        };
      }
    });
    this.canCreate = this.authService.isAllowed(ScopeType.ANY, ResourceType.USER, OperationType.CREATE);
    this.initData();
  }

  ngOnDestroy() {
    this.destroy$.next(true);
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getUsers();
  }

  handleTableClick(id: string) {
    this.router.navigate([routePaths.user, id]);
  }

  private async initData() {
    await this.getUsers();
    this.isLoading = false;
  }

  private async getUsers() {
    const result = await this.userService.getPaginatedUsers(this.currentPage, { sort: UserSortProperties.Username });
    this.table = {
      columns: [
        { id: 'username', label: this.translateService.instant('user.username') },
        { id: 'firsname', label: this.translateService.instant('user.first-name') },
        { id: 'lastname', label: this.translateService.instant('user.last-name') },
        { id: 'email', label: this.translateService.instant('user.email') }
      ],
      rows: result.data.map((_) => ({
        id: _.id.toString(),
        columnData: {
          username: _.username,
          firstname: _.firstname,
          email: _.email
        }
      }))
    };
    this.pagination = result.links;
  }
}
