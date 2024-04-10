import { Component, Input, OnChanges } from '@angular/core';
import { Visualization } from 'src/app/models/api/algorithm.model';

@Component({
  selector: 'app-visualize-table',
  templateUrl: './visualize-table.component.html',
  styleUrls: ['./visualize-table.component.scss']
})
export class VisualizeTableComponent implements OnChanges {
  @Input() visualization?: Visualization | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  @Input() result: any[] = [];

  columns: string[] = [];
  rows: string[][] = [];
  name?: string;
  description?: string;

  ngOnChanges(): void {
    // if the result is found at a key, use that key. E.g. if the result is { data: [1, 2, 3] },
    // location should be ['data'] to get the array
    let table_data = this.result;
    if (this.visualization?.schema?.location) {
      this.visualization.schema.location.forEach((key: any) => {
        table_data = table_data[key];
      });
    }

    // if columns are defined, use them. Otherwise use the keys of the first result
    if (this.visualization?.schema?.columns) {
      this.columns = this.visualization.schema.columns;
    } else {
      this.columns = Object.keys(table_data[0]);
    }
    this.rows = table_data;

    // set table name and description
    this.name = this.visualization?.name;
    this.description = this.visualization?.description;
  }
}
