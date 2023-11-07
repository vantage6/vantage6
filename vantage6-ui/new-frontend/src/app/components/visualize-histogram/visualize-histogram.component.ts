/* eslint-disable @typescript-eslint/no-explicit-any */
import { AfterViewInit, Component, ElementRef, Input, OnChanges, ViewChild } from '@angular/core';
import { Output } from 'src/app/models/api/algorithm.model';
import * as Plot from '@observablehq/plot';

@Component({
  selector: 'app-visualize-histogram',
  templateUrl: './visualize-histogram.component.html',
  styleUrls: ['./visualize-histogram.component.scss']
})
export class VisualizeHistogramComponent implements OnChanges, AfterViewInit {
  @ViewChild('histogram') container?: ElementRef;
  @Input() output!: Output;
  @Input() result!: any;

  ngOnChanges(): void {
    this.drawHistogram();
  }

  ngAfterViewInit(): void {
    this.drawHistogram();
  }

  private drawHistogram(): void {
    if (!this.container) return;
    const keys = Object.keys(this.result).filter((key) => !key.startsWith('_'));
    const values = keys.map((key) => {
      return { x: key, y: this.result[key] };
    });
    const plot = Plot.plot({
      y: { grid: true, label: null },
      x: { type: 'band', domain: keys, padding: 0, label: null },
      marks: [Plot.ruleY([0]), Plot.barY(values, { x: 'x', y: 'y', fill: '#3571af', stroke: '#000' })]
    });
    this.container.nativeElement.append(plot);
  }
}
