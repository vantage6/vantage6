import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { PageEvent, MatPaginator } from '@angular/material/paginator';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { StoreUser } from 'src/app/models/api/store-user.model';
import { Column, TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { StoreUserService } from 'src/app/services/store-user.service';
import { PermissionService } from 'src/app/services/permission.service';
import { StoreReview } from 'src/app/models/api/review.model';
import { StoreReviewService } from 'src/app/services/store-review.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatCard, MatCardContent, MatCardHeader, MatCardTitle } from '@angular/material/card';
import { MatButton } from '@angular/material/button';
import { NgIf } from '@angular/common';
import { MatIcon } from '@angular/material/icon';
import { TableComponent } from '../../../../components/table/table.component';

enum TableRows {
  ID = 'id',
  Name = 'name',
  Status = 'status'
}

@Component({
  selector: 'app-my-pending-algorithms',
  templateUrl: './my-pending-algorithms.component.html',
  styleUrl: './my-pending-algorithms.component.scss',
  standalone: true,
  imports: [
    PageHeaderComponent,
    MatCard,
    MatCardContent,
    MatButton,
    RouterLink,
    NgIf,
    MatIcon,
    MatCardHeader,
    MatCardTitle,
    TableComponent,
    MatPaginator,
    TranslateModule
  ]
})
export class MyPendingAlgorithmsComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  destroy$ = new Subject<void>();
  isLoading: boolean = true;
  loggedInStoreUser: StoreUser | null = null;
  store: AlgorithmStore | null = null;
  routes = routePaths;

  algorithmsInReviewProcess: Algorithm[] = [];
  canAssignReviewers: boolean = false;
  canAddAlgorithm = false;

  myPendingAlgorithms: Algorithm[] = [];
  myAlgorithmsTable?: TableData;

  myReviews: StoreReview[] = [];
  reviewTable?: TableData;
  paginationReview: PaginationLinks | null = null;
  currentPageInReview: number = 1;

  algorithmsAwaitingReview: Algorithm[] = [];
  algorithmAwaitingReviewTable?: TableData;
  paginationToBeReviewed: PaginationLinks | null = null;
  currentPageToBeReviewed: number = 1;

  constructor(
    private router: Router,
    private algorithmService: AlgorithmService,
    private storeUserService: StoreUserService,
    private chosenStoreService: ChosenStoreService,
    private storePermissionService: StorePermissionService,
    private translateService: TranslateService,
    private permissionService: PermissionService,
    private storeReviewService: StoreReviewService
  ) {}

  async ngOnInit() {
    this.storePermissionService.initialized$.pipe(takeUntil(this.destroy$)).subscribe((initialized) => {
      if (initialized) {
        this.initData(this.currentPageInReview, this.currentPageToBeReviewed);
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
  }

  private async initData(pageInReview: number, pageToBeReviewed: number): Promise<void> {
    this.store = this.chosenStoreService.store$.value;
    if (!this.store) return;

    this.canAssignReviewers = this.storePermissionService.isAllowed(StoreResourceType.REVIEW, OperationType.CREATE);
    this.canAddAlgorithm = this.storePermissionService.isAllowed(StoreResourceType.ALGORITHM, OperationType.CREATE);

    await this.setLoggedInStoreUser();

    await this.setAlgorithms();

    // TODO initalize tables simultaneously
    await this.initializeReviewTable(pageInReview);

    if (this.canAssignReviewers) {
      await this.initializeReviewAssignTable(pageToBeReviewed);
    }

    // TODO setup proper pagination in this table
    await this.initializeMyAlgorithmTable();

    this.isLoading = false;
  }

  private async setAlgorithms(): Promise<void> {
    if (!this.store) return;
    this.algorithmsInReviewProcess = await this.algorithmService.getAlgorithmsForAlgorithmStore(this.store, {
      in_review_process: true
    });
  }

  private async setLoggedInStoreUser(): Promise<void> {
    if (!this.store) return;
    const result = await this.storeUserService.getUsers(this.store.url, { username: this.permissionService.activeUser?.username });
    if (result.length > 0) {
      this.loggedInStoreUser = result[0];
    }
  }

  private async initializeReviewTable(pageInReview: number): Promise<void> {
    if (!this.store) return;

    const reviews = await this.storeReviewService.getPaginatedReviews(this.store.url, pageInReview, {
      reviewer_id: this.loggedInStoreUser?.id,
      under_review: true
    });
    this.myReviews = reviews.data;
    this.paginationReview = reviews.links;

    // add algorithms to reviews
    this.myReviews.forEach((review) => {
      review.algorithm = this.algorithmsInReviewProcess.find((algorithm) => algorithm.id === review.algorithm_id);
    });

    this.reviewTable = {
      columns: this.getSharedColumns(),
      rows: this.myReviews.map((review) => ({
        id: review.algorithm_id.toString(),
        columnData: {
          id: review.algorithm_id.toString(),
          name: review.algorithm?.name || this.translateService.instant('general.unknown')
        }
      }))
    };
  }

  private async initializeReviewAssignTable(pageToBeReviewed: number): Promise<void> {
    if (!this.store) return;
    this.isLoading = true;

    // get algorithms awaiting review
    const algorithmsAwaitingReview = await this.algorithmService.getPaginatedAlgorithms(this.store, pageToBeReviewed, {
      awaiting_reviewer_assignment: true
    });
    this.algorithmsAwaitingReview = algorithmsAwaitingReview.data;
    this.paginationToBeReviewed = algorithmsAwaitingReview.links;
    this.algorithmAwaitingReviewTable = {
      columns: [...this.getSharedColumns()],
      rows: this.algorithmsAwaitingReview.map((algorithm) => ({
        id: algorithm.id.toString(),
        columnData: {
          ...this.getRowData(algorithm)
        }
      }))
    };
  }

  private async initializeMyAlgorithmTable(): Promise<void> {
    this.myPendingAlgorithms = this.algorithmsInReviewProcess.filter((algorithm) => algorithm.developer_id === this.loggedInStoreUser?.id);

    this.myAlgorithmsTable = {
      columns: [
        { id: TableRows.ID, label: this.translateService.instant('general.id') },
        { id: TableRows.Name, label: this.translateService.instant('my-pending-algorithms.algorithm-name') },
        { id: TableRows.Status, label: this.translateService.instant('algorithm-in-review.status') }
      ],
      rows: this.myPendingAlgorithms.map((algorithm) => ({
        id: algorithm.id.toString(),
        columnData: {
          id: algorithm.id.toString(),
          name: algorithm.name,
          status: algorithm.status
        }
      }))
    };
  }

  handlePageEventInReview(e: PageEvent) {
    this.currentPageInReview = e.pageIndex + 1;
    this.initializeReviewTable(this.currentPageInReview);
  }

  handlePageEventToBeReviewed(e: PageEvent) {
    this.currentPageToBeReviewed = e.pageIndex + 1;
    this.initializeReviewAssignTable(this.currentPageToBeReviewed);
  }

  handleTableAwaitingReviewClick(algorithmID: string) {
    if (!this.storePermissionService.isAllowed(StoreResourceType.REVIEW, OperationType.CREATE)) {
      return;
    }
    this.router.navigate([routePaths.algorithmReviewAssign, algorithmID]);
  }

  handleTableInReviewClick(algorithmID: string) {
    if (!this.storePermissionService.isAllowed(StoreResourceType.REVIEW, OperationType.VIEW)) {
      return;
    }
    this.router.navigate([routePaths.algorithmReview, algorithmID]);
  }

  handleAlgorithmDevTableClick(algorithmID: string) {
    this.router.navigate([routePaths.algorithmManage, algorithmID]);
  }

  private getSharedColumns(): Column[] {
    return [
      { id: TableRows.ID, label: this.translateService.instant('general.id') },
      { id: TableRows.Name, label: this.translateService.instant('my-pending-algorithms.algorithm-name') }
    ];
  }

  private getRowData(algorithm: Algorithm): object {
    return {
      id: algorithm.id.toString(),
      name: algorithm.name
    };
  }
}
