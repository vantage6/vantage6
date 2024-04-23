import { Component, HostBinding, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { BaseAlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmStoreService } from 'src/app/services/algorithm-store.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';

@Component({
  selector: 'app-algorithm-store-list',
  templateUrl: './algorithm-store-list.component.html',
  styleUrl: './algorithm-store-list.component.scss'
})
export class AlgorithmStoreListComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  isLoading = true;
  algorithmStores: BaseAlgorithmStore[] = [];

  constructor(
    private router: Router,
    private algorithmStoreService: AlgorithmStoreService,
    private chosenStoreService: ChosenStoreService
  ) {}

  async ngOnInit() {
    await this.initData();
    this.isLoading = false;
  }

  handleAlgorithmStoreClick(store: BaseAlgorithmStore) {
    this.chosenStoreService.setStore(store.id.toString());
    this.router.navigate([routePaths.store]);
  }

  private async initData(): Promise<void> {
    this.algorithmStores = await this.algorithmStoreService.getAlgorithmStores();
  }
}
