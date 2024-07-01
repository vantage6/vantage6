import { Component, HostBinding, Input } from '@angular/core';
import { Subject } from 'rxjs';
import { Algorithm, AlgorithmFunction } from 'src/app/models/api/algorithm.model';
import { Visualization } from 'src/app/models/api/visualization.model';
import { routePaths } from 'src/app/routes';

@Component({
  selector: 'app-display-algorithm',
  templateUrl: './display-algorithm.component.html',
  styleUrl: './display-algorithm.component.scss'
})
export class DisplayAlgorithmComponent {
  @HostBinding('class') class = 'card-container';
  @Input() algorithm: Algorithm | undefined;
  destroy$ = new Subject<void>();

  routes = routePaths;

  selectedFunction?: AlgorithmFunction;

  selectFunction(functionId: number): void {
    this.selectedFunction = this.algorithm?.functions.find((func: AlgorithmFunction) => func.id === functionId);
  }

  getVisualizationSchemaAsText(vis: Visualization): string {
    return JSON.stringify(vis.schema);
  }
}
