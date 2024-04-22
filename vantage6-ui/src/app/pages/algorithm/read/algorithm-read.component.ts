import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Algorithm, AlgorithmFunction } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { AlgorithmStoreService } from 'src/app/services/algorithm-store.service';
import { AlgorithmService } from 'src/app/services/algorithm.service';

@Component({
  selector: 'app-algorithm-read',
  templateUrl: './algorithm-read.component.html',
  styleUrl: './algorithm-read.component.scss'
})
export class AlgorithmReadComponent implements OnInit {
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
    private algorithmStoreService: AlgorithmStoreService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.isLoading = false;
  }

  private async initData(): Promise<void> {
    this.algorithm_store = await this.algorithmStoreService.getAlgorithmStore(this.algo_store_id);
    if (!this.algorithm_store) return;

    this.algorithm = await this.algorithmService.getAlgorithm(this.algorithm_store.url, this.id);
  }
}
