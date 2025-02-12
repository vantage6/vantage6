import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { Algorithm, AlgorithmFunction, AlgorithmLazyProperties, AlgorithmStatus } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { HandleConfirmDialogService } from 'src/app/services/handle-confirm-dialog.service';
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
  routes = routePaths;

  algorithm?: Algorithm;
  algorithm_store?: AlgorithmStore;
  selectedFunction?: AlgorithmFunction;
  algorithmStatus = AlgorithmStatus;
  isLoading = true;

  canEdit = false;
  canDelete = false;
  canAssignReviewers: boolean = false;
  canViewReviews: boolean = false;

  constructor(
    private router: Router,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private algorithmService: AlgorithmService,
    private chosenStoreService: ChosenStoreService,
    private storePermissionService: StorePermissionService,
    private handleConfirmDialogService: HandleConfirmDialogService
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

  getLabelForAssignReviewers(): string {
    const commonText = this.translateService.instant('algorithm-read.alert.assign-review.common-content');
    if (this.algorithm?.reviews && this.algorithm?.reviews?.length > 0) {
      return `${commonText} ${this.translateService.instant('algorithm-read.alert.assign-review.content-insufficient-reviewers', { current_num_reviews: this.algorithm.reviews.length })}`;
    }
    return commonText;
  }

  private async initData(): Promise<void> {
    const chosenStore = this.chosenStoreService.store$.value;
    if (!chosenStore) return;

    this.algorithm = await this.algorithmService.getAlgorithm(chosenStore.url, this.id, [AlgorithmLazyProperties.Reviews]);

    this.canEdit = this.storePermissionService.isAllowed(StoreResourceType.ALGORITHM, OperationType.EDIT);
    this.canDelete = this.storePermissionService.isAllowed(StoreResourceType.ALGORITHM, OperationType.DELETE);
    this.canAssignReviewers = this.storePermissionService.isAllowed(StoreResourceType.REVIEW, OperationType.CREATE);
    this.canViewReviews = this.storePermissionService.isAllowed(StoreResourceType.REVIEW, OperationType.VIEW);

    this.isLoading = false;
  }

  handleDelete(): void {
    const store = this.chosenStoreService.store$.value;
    if (!this.algorithm || !store) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('algorithm-read.delete-dialog.title', { name: this.algorithm.name, store: store.name }),
        content: this.translateService.instant('algorithm-read.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === true) {
          if (!this.algorithm) return;
          this.isLoading = true;
          await this.algorithmService.deleteAlgorithm(this.algorithm.id.toString());
          this.router.navigate([routePaths.algorithmsManage]);
        }
      });
  }

  handleInvalidate(): void {
    this.handleConfirmDialogService.handleConfirmDialog(
      this.translateService.instant('algorithm-read.invalidate-dialog.title', { name: this.algorithm?.name }),
      this.translateService.instant('algorithm-read.invalidate-dialog.content'),
      this.translateService.instant('algorithm-read.invalidate'),
      'warn',
      async () => {
        if (!this.algorithm) return;
        this.isLoading = true;
        await this.algorithmService.invalidateAlgorithm(this.algorithm.id.toString());
        this.initData();
      }
    );
  }

  getButtonLink(route: string, id: number | undefined): string {
    return `${route}/${id}`;
  }

  showInvalidatedAlert(): boolean {
    if (!this.algorithm) return false;
    return ![AlgorithmStatus.Approved, AlgorithmStatus.AwaitingReviewerAssignment, AlgorithmStatus.UnderReview].includes(
      this.algorithm.status
    );
  }
}
