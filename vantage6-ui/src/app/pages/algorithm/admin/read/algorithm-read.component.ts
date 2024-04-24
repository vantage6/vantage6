import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { Subject, takeUntil } from 'rxjs';
import { Algorithm, AlgorithmFunction } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';

@Component({
  selector: 'app-algorithm-read',
  templateUrl: './algorithm-read.component.html',
  styleUrl: './algorithm-read.component.scss'
})
export class AlgorithmReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id: string = '';
  destroy$ = new Subject<void>();

  algorithm?: Algorithm;
  algorithm_store?: AlgorithmStore;
  selectedFunction?: AlgorithmFunction;
  isLoading = true;

  canEdit = false;
  canDelete = false;

  constructor(
    private algorithmService: AlgorithmService,
    private chosenStoreService: ChosenStoreService,
    private storePermissionService: StorePermissionService
  ) {}

  async ngOnInit(): Promise<void> {
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
    const chosenStore = this.chosenStoreService.store$.value;
    if (!chosenStore) return;

    this.algorithm = await this.algorithmService.getAlgorithm(chosenStore.url, this.id);

    this.canEdit = this.storePermissionService.isAllowed(StoreResourceType.ALGORITHM, OperationType.EDIT);
    this.canDelete = this.storePermissionService.isAllowed(StoreResourceType.ALGORITHM, OperationType.DELETE);

    this.isLoading = false;
  }

  handleDelete(): void {
    // TODO implement delete functionality
  }
}
