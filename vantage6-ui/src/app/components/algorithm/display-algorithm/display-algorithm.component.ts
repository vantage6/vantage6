import { Component, HostBinding, Input } from '@angular/core';
import { Algorithm, AlgorithmFunction } from 'src/app/models/api/algorithm.model';
import { Visualization } from 'src/app/models/api/visualization.model';

@Component({
  selector: 'app-display-algorithm',
  templateUrl: './display-algorithm.component.html',
  styleUrl: './display-algorithm.component.scss'
})
export class DisplayAlgorithmComponent {
  @HostBinding('class') class = 'card-container';
  @Input() algorithm: Algorithm | undefined;
  selectedFunction?: AlgorithmFunction;

  selectFunction(functionId: number): void {
    this.selectedFunction = this.algorithm?.functions.find((func: AlgorithmFunction) => func.id === functionId);
  }

  getVisualizationSchemaAsText(vis: Visualization): string {
    return JSON.stringify(vis.schema);
  }
}
