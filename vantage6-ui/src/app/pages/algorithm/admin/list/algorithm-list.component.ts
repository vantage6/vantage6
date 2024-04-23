import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { Subject, takeUntil } from 'rxjs';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';

@Component({
  selector: 'app-algorithm-list',
  templateUrl: './algorithm-list.component.html',
  styleUrl: './algorithm-list.component.scss'
})
export class AlgorithmListComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  isLoading = true;
  routePaths = routePaths;
  destroy$ = new Subject<void>();

  algorithms: Algorithm[] = [];
  stores: AlgorithmStore[] = [];

  constructor(
    private algorithmService: AlgorithmService,
    private chosenStoreService: ChosenStoreService
  ) {}

  async ngOnInit() {
    this.chosenStoreService.isInitialized$.pipe(takeUntil(this.destroy$)).subscribe((initialized) => {
      if (initialized) {
        this.initData();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
  }

  private async initData(): Promise<void> {
    const store = this.chosenStoreService.store$.value;
    if (!store) return;

    this.algorithms = await this.algorithmService.getAlgorithmsForAlgorithmStore(store);
    this.isLoading = false;
  }
}
