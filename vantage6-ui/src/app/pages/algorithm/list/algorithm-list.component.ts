import { Component, HostBinding, OnInit } from '@angular/core';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { AlgorithmService } from 'src/app/services/algorithm.service';

@Component({
  selector: 'app-algorithm-list',
  templateUrl: './algorithm-list.component.html',
  styleUrl: './algorithm-list.component.scss'
})
export class AlgorithmListComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  isLoading = true;
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
