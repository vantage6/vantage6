import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';

@Component({
  selector: 'app-algorithm-store-read',
  templateUrl: './algorithm-store-read.component.html',
  styleUrl: './algorithm-store-read.component.scss'
})
export class AlgorithmStoreReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';
  routePaths = routePaths;
  destroy$ = new Subject<void>();

  algorithmStore?: AlgorithmStore | null;
  algorithms?: Algorithm[];
  isLoading = true;
  collaborationTable?: TableData;

  constructor(
    private algorithmService: AlgorithmService,
    private translateService: TranslateService,
    private chosenStoreService: ChosenStoreService
  ) {}

  async ngOnInit(): Promise<void> {
    this.chosenStoreService.isInitialized$.pipe(takeUntil(this.destroy$)).subscribe((initialized) => {
      if (initialized) {
        this.initData();
      }
    });
    await this.initData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
  }

  private async initData(): Promise<void> {
    this.algorithmStore = this.chosenStoreService.store$.value;
    if (!this.algorithmStore) return;

    if (this.algorithmStore.collaborations) {
      this.collaborationTable = {
        columns: [{ id: 'name', label: this.translateService.instant('general.name') }],
        rows: this.algorithmStore.collaborations.map((collab) => ({
          id: collab.id.toString(),
          columnData: {
            name: collab.name
          }
        }))
      };
    }

    // collect algorithms
    this.algorithms = await this.algorithmService.getAlgorithmsForAlgorithmStore(this.algorithmStore);
    this.isLoading = false;
  }
}
