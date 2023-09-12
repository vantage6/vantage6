import { Component, Input, OnChanges } from '@angular/core';
import { Output, OutputVisualizeType } from 'src/app/models/api/algorithm.model';

@Component({
  selector: 'app-visualize-result',
  templateUrl: './visualize-result.component.html',
  styleUrls: ['./visualize-result.component.scss']
})
export class VisualizeResultComponent implements OnChanges {
  outputVisualizeType = OutputVisualizeType;

  @Input() functionOutput?: Output;
  @Input() result: string = '';

  columns: string[] = [];
  data: any[] = [];

  ngOnChanges(): void {
    this.columns = this.functionOutput?.keys || [];
    //TODO: use result to determine data
  }
}
