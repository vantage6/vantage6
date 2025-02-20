import { Component, Input, OnChanges } from '@angular/core';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { isNested } from 'src/app/helpers/utils.helper';
import { parseDefaultPandasFormat } from 'src/app/helpers/visualization.helper';
import { Visualization } from 'src/app/models/api/visualization.model';
import { FileService } from 'src/app/services/file.service';
import {
  MatTable,
  MatColumnDef,
  MatHeaderCellDef,
  MatHeaderCell,
  MatCellDef,
  MatCell,
  MatHeaderRowDef,
  MatHeaderRow,
  MatRowDef,
  MatRow
} from '@angular/material/table';
import { NgFor } from '@angular/common';
import { MatButton } from '@angular/material/button';

@Component({
    selector: 'app-visualize-table',
    templateUrl: './visualize-table.component.html',
    styleUrls: ['./visualize-table.component.scss'],
    imports: [
        MatTable,
        NgFor,
        MatColumnDef,
        MatHeaderCellDef,
        MatHeaderCell,
        MatCellDef,
        MatCell,
        MatHeaderRowDef,
        MatHeaderRow,
        MatRowDef,
        MatRow,
        MatButton,
        TranslateModule
    ]
})
export class VisualizeTableComponent implements OnChanges {
  @Input() visualization?: Visualization | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  @Input() result: any[] = [];
  @Input() result_id: string = '';

  columns: string[] = [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  rows: any[] = [];
  name?: string;
  description?: string;

  constructor(
    private fileService: FileService,
    private translateService: TranslateService
  ) {}

  ngOnChanges(): void {
    // if the result is found at a key, use that key. E.g. if the result is { data: [1, 2, 3] },
    // location should be ['data'] to get the array
    let tableData = this.result;
    if (this.visualization?.schema?.location) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      this.visualization.schema.location.forEach((key: any) => {
        tableData = tableData[key];
      });
    }

    // if tableData is JSON, parse it
    if (typeof tableData === 'string') {
      tableData = JSON.parse(tableData);
    }

    // check if data is formatted as {'A': {0: 1, 1: 2}, 'B': {0: 3, 1: 4}} (default for pandas DataFrame export
    // to json) or if it is formatted as [{'A': 1, 'B': 3}, {'A': 2, 'B': 4}] (orient='records' for pandas DataFrame)
    if (!Array.isArray(tableData) && isNested(tableData)) {
      this.parseDefaultPandasFormat(tableData);
    } else {
      this.parseRecordsFormat(tableData);
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private parseDefaultPandasFormat(tableData: any): void {
    let columns = null;
    if (this.schemaDefinesColumns()) {
      columns = this.visualization?.schema.columns as string[];
    }
    const parsedData = parseDefaultPandasFormat(tableData, this.translateService.instant('general.parameter'), columns);
    this.columns = parsedData.columns;
    this.rows = parsedData.rows;
  }

  //eslint-disable-next-line @typescript-eslint/no-explicit-any
  private parseRecordsFormat(tableData: any): void {
    // if the result is a single table row, convert it to an array of rows
    if (!Array.isArray(tableData)) {
      tableData = [tableData];
    }

    // if columns are defined, use them. Otherwise use the keys of the first result
    if (this.schemaDefinesColumns()) {
      this.columns = this.visualization?.schema.columns as string[];
    } else {
      this.columns = Object.keys(tableData[0]);
    }
    this.rows = tableData;

    // set table name and description
    this.name = this.visualization?.name;
    this.description = this.visualization?.description;
  }

  private schemaDefinesColumns(): boolean {
    return (
      this.visualization?.schema?.columns !== undefined &&
      Array.isArray(this.visualization.schema.columns) &&
      this.visualization.schema.columns.length > 0
    );
  }

  exportToCsv(): void {
    // Convert data to CSV format
    let csvData = this.columns.join(',') + '\n';
    this.rows.forEach((row) => {
      csvData += Object.values(row).join(',') + '\n';
    });

    this.fileService.downloadCsvFile(csvData, `vantage6_results_${this.result_id}.csv`);
  }
}
