/* eslint-disable @typescript-eslint/no-explicit-any */
import { Component, Input, OnChanges } from '@angular/core';
import { Output, OutputVisualizeType } from 'src/app/models/api/algorithm.model';

interface VisualizeResult {
  output: Output;
  results: any[];
}

@Component({
  selector: 'app-visualize-result',
  templateUrl: './visualize-result.component.html'
})
export class VisualizeResultComponent implements OnChanges {
  outputVisualizeType = OutputVisualizeType;

  @Input() functionOutput: Output | null = null;
  @Input() result: string = '';

  visualizeResults: VisualizeResult[] = [];

  ngOnChanges(): void {
    if (!this.functionOutput || !this.result) return;
    this.visualizeResults = [];

    const visualizeResult = {
      output: this.functionOutput,
      results: this.getFilteredResults(this.functionOutput)
    };
    this.visualizeResults.push(visualizeResult);
  }

  private getFilteredResults(output: Output): any[] {
    const filteredResults: any[] = [];
    const decodedResult: any = JSON.parse(atob(this.result || ''));

    Object.keys(decodedResult).forEach((key) => {
      if (decodedResult[key]) {
        if (output.filter_property) {
          if (decodedResult[key][output.filter_property] === output.filter_value) {
            filteredResults.push({ _row: key, ...decodedResult[key] });
          }
        } else {
          filteredResults.push({ _row: key, ...decodedResult[key] });
        }
      }
    });
    return filteredResults;
  }
}
