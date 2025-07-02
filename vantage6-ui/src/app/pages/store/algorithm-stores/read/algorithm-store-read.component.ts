import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { combineLatest, Subject, takeUntil } from 'rxjs';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore, AvailableStorePolicies, StorePolicies } from 'src/app/models/api/algorithmStore.model';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
// import { AlgorithmStore, AvailableStorePolicies, DefaultStorePolicies } from 'src/app/models/api/algorithmStore.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmStoreService } from 'src/app/services/algorithm-store.service';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { NgIf } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { TableComponent } from '../../../../components/table/table.component';
import { MatButton } from '@angular/material/button';
import { RouterLink } from '@angular/router';
import { MatIcon } from '@angular/material/icon';
import { DisplayAlgorithmsComponent } from '../../../../components/algorithm/display-algorithms/display-algorithms.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-algorithm-store-read',
  templateUrl: './algorithm-store-read.component.html',
  styleUrl: './algorithm-store-read.component.scss',
  imports: [
    NgIf,
    PageHeaderComponent,
    MatCard,
    MatCardHeader,
    MatCardTitle,
    MatCardContent,
    TableComponent,
    MatButton,
    RouterLink,
    MatIcon,
    DisplayAlgorithmsComponent,
    MatProgressSpinner,
    TranslateModule
  ]
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
  canAddAlgorithm = false;

  constructor(
    private algorithmService: AlgorithmService,
    private translateService: TranslateService,
    private chosenStoreService: ChosenStoreService,
    private algorithmStoreService: AlgorithmStoreService,
    private storePermissionService: StorePermissionService
  ) {}

  async ngOnInit(): Promise<void> {
    const chosenStore = this.chosenStoreService.getCurrentStore();
    const storePermissionInit = this.storePermissionService.isInitialized();
    combineLatest([chosenStore, storePermissionInit])
      .pipe(takeUntil(this.destroy$))
      .subscribe(([isChosenStoreInitialized, isStorePermissionInitialized]) => {
        if (isChosenStoreInitialized && isStorePermissionInitialized) {
          this.initData();
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
  }

  getMessageNoAlgorithms(): string {
    if (!this.storePermissionService.canViewAlgorithms) {
      return this.translateService.instant('algorithm-store-read.card-algorithms.no-algorithm-view-permission');
    }
    return this.translateService.instant('algorithm-store-read.card-algorithms.no-algorithms');
  }

  private async initData(): Promise<void> {
    this.algorithmStore = this.chosenStoreService.store$.value;
    if (!this.algorithmStore) return;

    this.canAddAlgorithm = this.storePermissionService.isAllowed(StoreResourceType.ALGORITHM, OperationType.CREATE);
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
    if (this.storePermissionService.canViewAlgorithms) {
      this.algorithms = await this.algorithmService.getAlgorithmsForAlgorithmStore(this.algorithmStore);
    }

    // get store policies
    await this.setPolicies();

    this.isLoading = false;
  }

  private async setPolicies(): Promise<void> {
    // collect store policies and convert from key|value to object with lists
    if (!this.algorithmStore) return;

    const getPublicPolicies = !this.storePermissionService.isUserRegistered;

    const policies = await this.algorithmStoreService.getAlgorithmStorePolicies(this.algorithmStore.url, getPublicPolicies);

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
    } else if (key === AvailableStorePolicies.ASSIGN_REVIEW_OWN_ALGORITHM) {
      return value ? this.translateService.instant('general.yes') : this.translateService.instant('general.no');
    } else if (key === AvailableStorePolicies.ALLOWED_REVIEWERS || key === AvailableStorePolicies.ALLOWED_REVIEW_ASSIGNERS) {
      return value === null ? this.translateService.instant('store-policies.not-defined') : value;
    } else if (Array.isArray(value)) {
      return value.join(', ');
    } else {
      return value.toString();
    }
  }
}
