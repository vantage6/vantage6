import { Component, HostBinding, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { getStoreUserParameters } from 'src/app/models/api/store-user.model';
import { GetUserParameters } from 'src/app/models/api/user.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { SearchRequest } from '../../table/table.component';
import { getApiSearchParameters } from 'src/app/helpers/api.helper';

@Component({
  selector: 'app-base-user-list',
  templateUrl: './base-user-list.component.html',
  styleUrl: './base-user-list.component.scss'
})
export abstract class BaseUserListComponent implements OnDestroy {
  @HostBinding('class') class = 'card-container';

  routes = routePaths;
  destroy$ = new Subject();

  isLoading: boolean = true;
  canCreate: boolean = false;
  table?: TableData;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;

  ngOnDestroy() {
    this.destroy$.next(true);
  }

  protected abstract initData(page: number, parameters: GetUserParameters | getStoreUserParameters): void;

  handleSearchChanged(searchRequests: SearchRequest[]): void {
    const parameters = getApiSearchParameters<GetUserParameters | getStoreUserParameters>(searchRequests);
    this.initData(1, parameters);
  }
}
