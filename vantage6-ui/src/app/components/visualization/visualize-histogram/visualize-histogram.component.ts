/* eslint-disable @typescript-eslint/no-explicit-any */
import { AfterViewInit, Component, ElementRef, Input, OnChanges, ViewChild } from '@angular/core';
import * as Plot from '@observablehq/plot';
import { Visualization } from 'src/app/models/api/visualization.model';

@Component({
  selector: 'app-visualize-histogram',
  templateUrl: './visualize-histogram.component.html',
  styleUrls: ['./visualize-histogram.component.scss'],
  standalone: true
})
export class VisualizeHistogramComponent implements OnChanges, AfterViewInit {
  @ViewChild('histogram') container?: ElementRef;
  @Input() visualization!: Visualization;
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
