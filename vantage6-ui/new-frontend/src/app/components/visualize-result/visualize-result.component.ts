/* eslint-disable @typescript-eslint/no-explicit-any */
import { Component, Input, OnChanges } from '@angular/core';
import { filter } from 'd3';
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
  @Input() result: any = '';

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
    // TODO This may not work for the case where the output is an array - fix that. Old code kept (but commented out) below

    // Object.keys(this.result).forEach((key) => {
    // console.log(this.result[key], this.result, key);
    // if (this.result[key]) {
    const filteredResult: any = { _row: 1, ...this.result };
    // if (output.filter_property) {
    //   if (this.result[key][output.filter_property] === output.filter_value) {
    //     filteredResult[key] = this.result[key];
    //   }
    // } else {
    // filteredResult[key] = this.result[key];
    // }
    filteredResults.push(filteredResult);
    // }
    // });
    return filteredResults;
  }
}
