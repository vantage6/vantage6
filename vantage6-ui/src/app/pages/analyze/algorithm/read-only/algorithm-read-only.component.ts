import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { Algorithm, AlgorithmFunction } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { NgIf } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatButton } from '@angular/material/button';
import { DisplayAlgorithmComponent } from '../../../../components/algorithm/display-algorithm/display-algorithm.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-algorithm-read-only',
  templateUrl: './algorithm-read-only.component.html',
  styleUrl: './algorithm-read-only.component.scss',
  imports: [NgIf, PageHeaderComponent, MatButton, DisplayAlgorithmComponent, MatCard, MatCardContent, MatProgressSpinner, TranslateModule]
})
export class AlgorithmReadOnlyComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id: string = '';
  @Input() algo_store_id: string = '';
  destroy$ = new Subject<void>();

  algorithm?: Algorithm;
  algorithm_store?: AlgorithmStore;
  selectedFunction?: AlgorithmFunction;
  isLoading = true;

  constructor(
    private router: Router,
    private algorithmService: AlgorithmService,
    private chosenCollaborationService: ChosenCollaborationService,
    private chosenStoreService: ChosenStoreService
  ) {}

  async ngOnInit(): Promise<void> {
    this.chosenCollaborationService.isInitialized$.pipe(takeUntil(this.destroy$)).subscribe((initialized) => {
      if (initialized) {
        this.initData();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
  }

  private async initData(): Promise<void> {
    const collaboration = this.chosenCollaborationService.collaboration$.getValue();
    if (!collaboration) return;

    this.algorithm_store = collaboration.algorithm_stores.find(
      (algorithmStore: AlgorithmStore) => algorithmStore.id.toString() === this.algo_store_id
    );
    if (!this.algorithm_store) return;

    this.algorithm = await this.algorithmService.getAlgorithm(this.algorithm_store, this.id);
    this.isLoading = false;
  }

  goToAlgorithm(algorithm: Algorithm): void {
    const chosenStore = this.chosenStoreService.store$.value;
    if (chosenStore && chosenStore.id.toString() === this.algo_store_id) {
      this.router.navigate([routePaths.algorithmManage, algorithm.id]);
    } else {
      this.router.navigate([routePaths.algorithmsManage]);
    }
  }
}
