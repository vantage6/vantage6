import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { Algorithm, AlgorithmFunction, AlgorithmStatus } from 'src/app/models/api/algorithm.model';
import { Visualization } from 'src/app/models/api/visualization.model';

@Component({
  selector: 'app-display-algorithm',
  templateUrl: './display-algorithm.component.html',
  styleUrl: './display-algorithm.component.scss'
})
export class DisplayAlgorithmComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  @Input() algorithm: Algorithm | undefined;
  selectedFunction?: AlgorithmFunction;
  algorithmApproved: boolean = false;

  ngOnInit(): void {
    this.algorithmApproved = this.algorithm?.status === AlgorithmStatus.Approved;
  }

  selectFunction(functionId: number): void {
    this.selectedFunction = this.algorithm?.functions.find((func: AlgorithmFunction) => func.id === functionId);
  }

  getVisualizationSchemaAsText(vis: Visualization): string {
    return JSON.stringify(vis.schema);
  }
}
