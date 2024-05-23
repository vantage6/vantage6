import { Component, HostBinding, OnInit } from '@angular/core';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';

@Component({
  selector: 'app-algorithm-list',
  templateUrl: './algorithm-list-read-only.component.html',
  styleUrl: './algorithm-list-read-only.component.scss'
})
export class AlgorithmListReadOnlyComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  isLoading = true;
  routePaths = routePaths;

  algorithms: Algorithm[] = [];
  stores: AlgorithmStore[] = [];

  constructor(private algorithmService: AlgorithmService) {}

  async ngOnInit() {
    await this.initData();
    this.isLoading = false;
  }

  private async initData(): Promise<void> {
    this.algorithms = await this.algorithmService.getAlgorithms();
  }
}
