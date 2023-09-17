import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { TableData } from 'src/app/models/application/table.model';

@Component({
  selector: 'app-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent implements OnChanges {
  @Input() data?: TableData;
  @Output() rowClick = new EventEmitter<string>();

  columnsToDisplay: string[] = [];

  ngOnChanges(): void {
    this.columnsToDisplay = this.data?.columns.map((column) => column.id) || [];
  }

  handleRowClick(row: any) {
    this.rowClick.emit(row.id);
  }
}
