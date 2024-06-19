import { Component, HostBinding, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { SearchRequest } from '../../table/table.component';
import { getApiSearchParameters } from 'src/app/helpers/api.helper';
import { ResourceGetParameters } from 'src/app/models/api/resource.model';

@Component({
  selector: 'app-base-list',
  templateUrl: './base-list.component.html',
  styleUrl: './base-list.component.scss'
})
export abstract class BaseListComponent implements OnDestroy {
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

  protected abstract initData(page: number, parameters: ResourceGetParameters): void;

  handleSearchChanged(searchRequests: SearchRequest[]): void {
    const parameters = getApiSearchParameters<ResourceGetParameters>(searchRequests);
    this.initData(1, parameters);
  }
}
