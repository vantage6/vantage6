import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { Subject, takeUntil } from 'rxjs';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';

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
  routes = routePaths;

  algorithms: Algorithm[] = [];

  canAddAlgorithm = false;

  constructor(
    private algorithmService: AlgorithmService,
    private chosenStoreService: ChosenStoreService,
    private storePermissionService: StorePermissionService
  ) {}

  async ngOnInit() {
    // note that we wait here for initialization of the store permission service rather than the chosen
    // collaboration service: this is because the store permission service is initialized after the chosen
    // collaboration service
    this.storePermissionService.initialized$.pipe(takeUntil(this.destroy$)).subscribe((initialized) => {
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

    this.canAddAlgorithm = this.storePermissionService.isAllowed(StoreResourceType.ALGORITHM, OperationType.CREATE);
    this.algorithms = await this.algorithmService.getAlgorithmsForAlgorithmStore(store);
    this.isLoading = false;
  }
}
