import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { PageEvent, MatPaginator } from '@angular/material/paginator';
import { Router } from '@angular/router';
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
import { assignDevelopersToAlgorithms } from '../review.helper';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { NgIf } from '@angular/common';
import { TableComponent } from '../../../../components/table/table.component';

enum TableRows {
  ID = 'id',
  Name = 'name',
  Developer = 'developer'
}

@Component({
    selector: 'app-algorithm-in-review-list',
    templateUrl: './algorithm-in-review-list.component.html',
    styleUrl: './algorithm-in-review-list.component.scss',
    imports: [PageHeaderComponent, MatCard, MatCardHeader, MatCardTitle, MatCardContent, NgIf, TableComponent, MatPaginator, TranslateModule]
})
export class AlgorithmInReviewListComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  destroy$ = new Subject<void>();
  isLoading: boolean = true;

  storeUsers: StoreUser[] = [];
  store: AlgorithmStore | null = null;

  algorithmsInReview: Algorithm[] = [];
  algorithmInReviewTable?: TableData;
  paginationInReview: PaginationLinks | null = null;
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
    private translateService: TranslateService
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

  private async setStoreUsers(): Promise<void> {
    if (!this.store) return;
    this.storeUsers = await this.storeUserService.getUsers(this.store.url);
  }

  private async initData(pageInReview: number, pageToBeReviewed: number): Promise<void> {
    this.store = this.chosenStoreService.store$.value;
    if (!this.store) return;
    await this.setStoreUsers();

    await this.initializeTable(pageInReview, pageToBeReviewed);
  }

  private async initializeTable(pageInReview: number, pageToBeReviewed: number): Promise<void> {
    if (!this.store) return;
    this.isLoading = true;
    // get algorithms awaiting review
    const algorithmsAwaitingReview = await this.algorithmService.getPaginatedAlgorithms(this.store, pageToBeReviewed, {
      awaiting_reviewer_assignment: true
    });
    this.algorithmsAwaitingReview = algorithmsAwaitingReview.data;
    this.algorithmsAwaitingReview = assignDevelopersToAlgorithms(this.algorithmsAwaitingReview, this.storeUsers);
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

    // get algorithms in review
    const algorithmsInReview = await this.algorithmService.getPaginatedAlgorithms(this.store, pageInReview, { under_review: true });
    this.algorithmsInReview = algorithmsInReview.data;
    this.paginationInReview = algorithmsInReview.links;
    this.algorithmsInReview = assignDevelopersToAlgorithms(this.algorithmsInReview, this.storeUsers);
    this.algorithmInReviewTable = {
      columns: [...this.getSharedColumns()],
      rows: this.algorithmsInReview.map((algorithm) => ({
        id: algorithm.id.toString(),
        columnData: {
          ...this.getRowData(algorithm)
        }
      }))
    };

    this.isLoading = false;
  }

  handlePageEventInReview(e: PageEvent) {
    this.currentPageInReview = e.pageIndex + 1;
    this.initData(this.currentPageInReview, this.currentPageToBeReviewed);
  }

  handlePageEventToBeReviewed(e: PageEvent) {
    this.currentPageToBeReviewed = e.pageIndex + 1;
    this.initData(this.currentPageInReview, this.currentPageToBeReviewed);
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

  private getSharedColumns(): Column[] {
    return [
      { id: TableRows.ID, label: this.translateService.instant('general.id') },
      { id: TableRows.Name, label: this.translateService.instant('general.name') },
      { id: TableRows.Developer, label: this.translateService.instant('algorithm-in-review.developer') }
    ];
  }

  private getRowData(algorithm: Algorithm): object {
    return {
      id: algorithm.id.toString(),
      name: algorithm.name,
      developer: algorithm.developer ? algorithm.developer.username : this.translateService.instant('general.unknown')
    };
  }
}
