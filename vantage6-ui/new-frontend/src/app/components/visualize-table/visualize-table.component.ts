import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-visualize-table',
  templateUrl: './visualize-table.component.html',
  styleUrls: ['./visualize-table.component.scss']
})
export class VisualizeTableComponent {
  @Input() columns: string[] = [];
  @Input() data: any[] = [];
}
