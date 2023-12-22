import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import { Subscription, debounceTime } from 'rxjs';
import { Column, TableData } from 'src/app/models/application/table.model';
import { WAIT_TABLE_SEARCH_TIME_MS } from 'src/app/models/constants/table';

export interface SearchRequest {
  columnId: string;
  searchString: string;
}

@Component({
  selector: 'app-table',
  styleUrls: ['./table.component.scss'],
  templateUrl: './table.component.html'
})
export class TableComponent implements OnChanges {
  @Input() data?: TableData;
  @Input() isLoading: boolean = false;
  @Output() rowClick = new EventEmitter<string>();
  @Output() searchChanged = new EventEmitter<SearchRequest[]>();

  columnsToDisplay: string[] = [];
  searchColumnsToDisplay: string[] = [];
  hasSearchColumns: boolean = false;
  searchForm: FormGroup = new FormGroup('');
  searchFormDescription?: Subscription;

  constructor(private translate: TranslateService) {}

  ngOnChanges(): void {
    this.columnsToDisplay = this.data?.columns.map((column) => column.id) || [];
    this.searchColumnsToDisplay = this.data?.columns.map((column) => `search-${column.id}`) || [];
    this.hasSearchColumns = !!this.data?.columns.find((column) => column.searchEnabled);
    this.initFormGroup();
  }

  getComponentClass(): string {
    const classes: string[] = [];
    if (this.isLoading) classes.push('searchable-table--is-loading');
    if (!this.hasSearchColumns) classes.push('searchable-table--has-no-search-columns');

    return classes.join(' ');
  }

  initFormGroup(): void {
    this.searchFormDescription?.unsubscribe();

    if (this.data) {
      const searchColumns: Column[] = this.data.columns.filter((column) => column.searchEnabled);
      if (searchColumns.length > 0) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const formControls: any = {};

        searchColumns.forEach((column) => {
          formControls[column.id] = new FormControl(column.initSearchString);
        });
        this.searchForm = new FormGroup(formControls);

        this.searchFormDescription = this.searchForm.statusChanges.pipe(debounceTime(WAIT_TABLE_SEARCH_TIME_MS)).subscribe(() => {
          const test = this.searchForm.getRawValue();
          const searchRequests: SearchRequest[] = Object.entries(test).map(([id, searchString]) => {
            return { columnId: id, searchString: searchString as string };
          });
          this.searchChanged.emit(searchRequests);
        });
      }
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleRowClick(row: any) {
    this.rowClick.emit(row.id);
  }

  getPlaceholder(column: Column): string {
    return `${this.translate.instant('table.search-placeholder')} ${column.label}`;
  }
}
