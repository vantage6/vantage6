import { Component, Input, OnChanges } from '@angular/core';
import { Visualization } from 'src/app/models/api/visualization.model';
import { FileService } from 'src/app/services/file.service';

@Component({
  selector: 'app-visualize-table',
  templateUrl: './visualize-table.component.html',
  styleUrls: ['./visualize-table.component.scss']
})
export class VisualizeTableComponent implements OnChanges {
  @Input() visualization?: Visualization | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  @Input() result: any[] = [];
  @Input() result_id: string = '';

  columns: string[] = [];
  rows: string[][] = [];
  name?: string;
  description?: string;

  constructor(private fileService: FileService) {}

  ngOnChanges(): void {
    // if the result is found at a key, use that key. E.g. if the result is { data: [1, 2, 3] },
    // location should be ['data'] to get the array
    let tableData = this.result;
    if (this.visualization?.schema?.location) {
      this.visualization.schema.location.forEach((key: any) => {
        tableData = tableData[key];
      });
    }

    // if the result is a single table row, convert it to an array of rows
    if (!Array.isArray(tableData)) {
      tableData = [tableData];
    }

    // if columns are defined, use them. Otherwise use the keys of the first result
    if (this.visualization?.schema?.columns) {
      this.columns = this.visualization.schema.columns;
    } else {
      this.columns = Object.keys(tableData[0]);
    }
    this.rows = tableData;

    // set table name and description
    this.name = this.visualization?.name;
    this.description = this.visualization?.description;
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
