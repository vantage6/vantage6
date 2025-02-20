import { Component, OnDestroy, OnInit } from '@angular/core';
import { takeUntil } from 'rxjs';
import { BaseListComponent } from 'src/app/components/admin-base/base-list/base-list.component';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf } from '@angular/common';
import { AlertComponent } from '../../../../components/alerts/alert/alert.component';
import { DisplayAlgorithmsComponent } from '../../../../components/algorithm/display-algorithms/display-algorithms.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-old-algorithm-list',
  templateUrl: './old-algorithm-list.component.html',
  styleUrl: './old-algorithm-list.component.scss',
  standalone: true,
  imports: [
    PageHeaderComponent,
    NgIf,
    AlertComponent,
    DisplayAlgorithmsComponent,
    MatCard,
    MatCardContent,
    MatProgressSpinner,
    TranslateModule
  ]
})
export class OldAlgorithmListComponent extends BaseListComponent implements OnInit, OnDestroy {
  oldAlgorithms: Algorithm[] = [];

  constructor(
    private algorithmService: AlgorithmService,
    private chosenStoreService: ChosenStoreService,
    private storePermissionService: StorePermissionService
  ) {
    super();
  }

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

  protected async initData(): Promise<void> {
    const store = this.chosenStoreService.store$.value;
    if (!store) return;

    this.oldAlgorithms = await this.algorithmService.getAlgorithmsForAlgorithmStore(store, { invalidated: true });
    this.isLoading = false;
  }
}
