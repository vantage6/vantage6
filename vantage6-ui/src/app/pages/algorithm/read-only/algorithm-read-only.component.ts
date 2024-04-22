import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Algorithm, AlgorithmFunction, Visualization } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';

@Component({
  selector: 'app-algorithm-read-only',
  templateUrl: './algorithm-read-only.component.html',
  styleUrl: './algorithm-read-only.component.scss'
})
export class AlgorithmReadOnlyComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  @Input() id: string = '';
  @Input() algo_store_id: string = '';

  algorithm?: Algorithm;
  algorithm_store?: AlgorithmStore;
  selectedFunction?: AlgorithmFunction;
  isLoading = true;

  constructor(
    private router: Router,
    private algorithmService: AlgorithmService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.isLoading = false;
  }

  selectFunction(functionId: number): void {
    this.selectedFunction = this.algorithm?.functions.find((func: AlgorithmFunction) => func.id === functionId);
  }

  private async initData(): Promise<void> {
    const collaboration = this.chosenCollaborationService.collaboration$.getValue();
    if (!collaboration) return;

    this.algorithm_store = collaboration.algorithm_stores.find(
      (algorithmStore: AlgorithmStore) => algorithmStore.id.toString() === this.algo_store_id
    );
    if (!this.algorithm_store) return;

    this.algorithm = await this.algorithmService.getAlgorithm(this.algorithm_store.url, this.id);
  }

  getVisualizationSchemaAsText(vis: Visualization): string {
    return JSON.stringify(vis.schema);
  }
}
