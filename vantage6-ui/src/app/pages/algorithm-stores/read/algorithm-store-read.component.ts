import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore, AvailableStorePolicies, DefaultStorePolicies } from 'src/app/models/api/algorithmStore.model';
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
    const policiesDict = await this.algorithmStoreService.getAlgorithmStorePolicies(this.algorithmStore.url);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const policies: { [key: string]: string } = {};
    for (const newPolicy of policiesDict) {
      const policy_name = newPolicy.key;

      if (policy_name in policies) {
        policies[policy_name] = `${policies[policy_name]}, ${newPolicy.value}`;
      } else {
        policies[policy_name] = newPolicy.value;
      }
    }

    // add default policies for any policies not present
    for (const policy of Object.keys(AvailableStorePolicies)) {
      if (!(policy.toLowerCase() in policies)) {
        policies[policy.toLowerCase()] = DefaultStorePolicies[policy as keyof typeof DefaultStorePolicies];
      }
    }

    this.policyTable = this.translatePoliciesToTable(policies);
  }

  private translatePoliciesToTable(policies: { [key: string]: string }): TableData {
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

  private translatePolicyValue(key: string, value: string): string {
    if (key === AvailableStorePolicies.ALGORITHM_VIEW) {
      return this.translateService.instant(`store-policies.${AvailableStorePolicies.ALGORITHM_VIEW}-values.${value}`);
    } else if (key === AvailableStorePolicies.ALLOW_LOCALHOST) {
      return value === '0' || value === 'false'
        ? this.translateService.instant('general.no')
        : this.translateService.instant('general.yes');
    } else {
      return value;
    }
  }
}
