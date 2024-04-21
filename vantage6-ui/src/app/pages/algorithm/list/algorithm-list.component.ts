import { Component, HostBinding, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';

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

  constructor(
    private router: Router,
    private chosenCollaborationService: ChosenCollaborationService,
    private algorithmService: AlgorithmService
  ) {}

  async ngOnInit() {
    await this.initData();
    this.isLoading = false;
  }

  handleAlgorithmClick(algorithm: Algorithm) {
    console.log('click');
  }

  private async initData(): Promise<void> {
    this.algorithms = await this.algorithmService.getAlgorithms();
  }
}
