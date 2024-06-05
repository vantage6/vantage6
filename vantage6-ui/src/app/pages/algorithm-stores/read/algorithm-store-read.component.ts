import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore, AvailableStorePolicies, StorePolicies } from 'src/app/models/api/algorithmStore.model';
// import { AlgorithmStore, AvailableStorePolicies, DefaultStorePolicies } from 'src/app/models/api/algorithmStore.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmStoreService } from 'src/app/services/algorithm-store.service';
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
  policyTable?: TableData;
  isLoading = true;
  collaborationTable?: TableData;

  constructor(
    private algorithmService: AlgorithmService,
    private translateService: TranslateService,
    private chosenStoreService: ChosenStoreService,
    private algorithmStoreService: AlgorithmStoreService
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

    // get store policies
    await this.setPolicies();

    this.isLoading = false;
  }

  private async setPolicies(): Promise<void> {
    // collect store policies and convert from key|value to object with lists
    if (!this.algorithmStore) return;
    const policies = await this.algorithmStoreService.getAlgorithmStorePolicies(this.algorithmStore.url);

    this.policyTable = this.translatePoliciesToTable(policies);
  }

  private translatePoliciesToTable(policies: StorePolicies): TableData {
    return {
      columns: [
        { id: 'name', label: this.translateService.instant('store-policies.type') },
        { id: 'value', label: this.translateService.instant('store-policies.policy') }
      ],
      rows: Object.keys(policies).map((key) => {
        return {
          id: key,
          columnData: {
            name: this.translatePolicyKey(key),
            value: this.translatePolicyValue(key, policies[key])
          }
        };
      })
    };
  }

  private translatePolicyKey(key: string): string {
    return this.translateService.instant(`store-policies.${key}`);
  }

  private translatePolicyValue(key: string, value: string | string[] | boolean): string {
    if (key === AvailableStorePolicies.ALGORITHM_VIEW) {
      return this.translateService.instant(`store-policies.${key}-values.${value}`);
    } else if (key === AvailableStorePolicies.ALLOW_LOCALHOST) {
      return value ? this.translateService.instant('general.yes') : this.translateService.instant('general.no');
    } else if (Array.isArray(value)) {
      return value.join(', ');
    } else {
      return value.toString();
    }
  }
}
