import { Component, Input, OnChanges } from '@angular/core';
import { Output } from 'src/app/models/api/algorithm.model';

@Component({
  selector: 'app-visualize-table',
  templateUrl: './visualize-table.component.html',
  styleUrls: ['./visualize-table.component.scss']
})
export class VisualizeTableComponent implements OnChanges {
  @Input() output?: Output;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  @Input() results: any[] = [];

  columns: string[] = [];
  rows: string[] = [];

  ngOnChanges(): void {
    this.results.forEach((result) => {
      const columns = this.output?.keys || Object.keys(result).filter((key) => !key.startsWith('_'));
      this.columns = ['_row', ...columns];

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const rows: any = {};
      columns.map((column) => {
        rows[column] = result[column];
      });
      this.rows.push({ _row: result._row, ...rows });
    });
  }
}
