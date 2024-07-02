import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { ReviewStatus, StoreReview } from 'src/app/models/api/review.model';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { StoreUser } from 'src/app/models/api/store-user.model';
import { BaseUser } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { PermissionService } from 'src/app/services/permission.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { StoreReviewService } from 'src/app/services/store-review.service';
import { StoreUserService } from 'src/app/services/store-user.service';

@Component({
  selector: 'app-review-read',
  templateUrl: './review-read.component.html',
  styleUrl: './review-read.component.scss'
})
export class ReviewReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';

  @Input() algoID: string = '';
  isLoading: boolean = true;
  destroy$ = new Subject<void>();
  routes = routePaths;

  algorithm: Algorithm | null = null;
  reviews: StoreReview[] = [];
  reviewers: StoreUser[] = [];
  loggedInUser: BaseUser | null = null;
  store: AlgorithmStore | null = null;

  canApprove: boolean = false;
  canDelete: boolean = false;
  canCreate: boolean = false;

  constructor(
    private chosenStoreService: ChosenStoreService,
    private algorithmService: AlgorithmService,
    private storePermissionService: StorePermissionService,
    private router: Router,
    private reviewService: StoreReviewService,
    private storeUserService: StoreUserService,
    private permissionService: PermissionService,
    private dialog: MatDialog,
    private translateService: TranslateService
  ) {}

  ngOnInit() {
    this.storePermissionService.initialized$.pipe(takeUntil(this.destroy$)).subscribe((initialized) => {
      if (initialized) {
        this.initData();
      }
    });
  }

  ngOnDestroy() {
    this.destroy$.next();
  }

  private async initData() {
    this.store = this.chosenStoreService.store$.value;
    if (!this.store) {
      return;
    }
    this.algorithm = await this.algorithmService.getAlgorithm(this.store.url, this.algoID);
    this.reviewers = await this.storeUserService.getUsers(this.store.url, { can_review: true });
    this.reviews = await this.reviewService.getReviews(this.store.url, { algorithm_id: this.algoID });

    this.canDelete = this.storePermissionService.isAllowed(StoreResourceType.REVIEW, OperationType.DELETE);
    this.canApprove = this.storePermissionService.isAllowed(StoreResourceType.ALGORITHM, OperationType.REVIEW);
    this.canCreate = this.storePermissionService.isAllowed(StoreResourceType.REVIEW, OperationType.CREATE);

    this.loggedInUser = this.permissionService.activeUser;

    this.isLoading = false;
  }

  isReviewFinished(review: StoreReview): boolean {
    return review.status !== ReviewStatus.UnderReview;
  }

  isAllowedToApprove(review: StoreReview) {
    if (!this.canApprove || this.isReviewFinished(review)) {
      return false;
    }
    // get the current logged in user and check if they are the reviewer
    if (!this.loggedInUser) {
      return false;
    }
    return this.loggedInUser.username === review.reviewer.username;
  }

  async handleDelete(review: StoreReview) {
    if (!this.canDelete || !this.store) {
      return;
    }

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('algorithm-review.delete-dialog.title', { reviewer: review.reviewer.username }),
        content: this.translateService.instant('algorithm-review.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === true) {
          if (!this.store) return;
          await this.reviewService.deleteReview(this.store.url, review.id).then(() => {
            this.reviews = this.reviews.filter((r) => r.id !== review.id);
          });
          if (this.reviews.length === 0) {
            this.router.navigate([this.routes.algorithmReviews]);
          }
        }
      });
  }
}
