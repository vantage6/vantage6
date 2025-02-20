/* eslint-disable @typescript-eslint/no-explicit-any */
import { Component, Input, OnChanges } from '@angular/core';
import { Visualization, VisualizationType } from 'src/app/models/api/visualization.model';
import { NgIf } from '@angular/common';
import { VisualizeTableComponent } from '../visualize-table/visualize-table.component';
import { VisualizeLineComponent } from '../visualize-line/visualize-line.component';

// interface VisualizeResult {
//   visualization: Visualization;
//   results: any[];
// }

@Component({
  selector: 'app-visualize-result',
  templateUrl: './visualize-result.component.html',
  standalone: true,
  imports: [NgIf, VisualizeTableComponent, VisualizeLineComponent]
})
export class VisualizeResultComponent implements OnChanges {
  visualizationType = VisualizationType;

  @Input() visualization?: Visualization | null;
  @Input() result: any = '';
  @Input() result_id: string = '';

  // visualizeResults: VisualizeResult[] = [];

  ngOnChanges(): void {
    // if (!this.visualization || !this.result) return;
    // this.visualizeResults = [];
    // console.log(this.result)
    // const visualizeResult = {
    //   visualization: this.visualization,
    //   results: this.result
    //   // results: this.getFilteredResults(this.visualization)
    // };
    // this.visualizeResults.push(visualizeResult);
  }

  // private getFilteredResults(visualization: Visualization): any[] {
  //   const filteredResults: any[] = [];
  //   // TODO This may not work for the case where the output is an array - fix that. Old code kept (but commented out) below

  //   // Object.keys(this.result).forEach((key) => {
  //   // console.log(this.result[key], this.result, key);
  //   // if (this.result[key]) {
  //   const filteredResult: any = { _row: 1, ...this.result };
  //   // if (output.filter_property) {
  //   //   if (this.result[key][output.filter_property] === output.filter_value) {
  //   //     filteredResult[key] = this.result[key];
  //   //   }
  //   // } else {
  //   // filteredResult[key] = this.result[key];
  //   // }
  //   filteredResults.push(filteredResult);
  //   // }
  //   // });
  //   return filteredResults;
  // }
}
