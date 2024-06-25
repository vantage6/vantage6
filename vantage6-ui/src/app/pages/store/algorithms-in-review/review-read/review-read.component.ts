import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { ReviewStatus, StoreReview } from 'src/app/models/api/review.model';
import { StoreUser } from 'src/app/models/api/store-user.model';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
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

  algorithm: Algorithm | null = null;
  reviews: StoreReview[] = [];
  reviewers: StoreUser[] = [];

  constructor(
    private chosenStoreService: ChosenStoreService,
    private algorithmService: AlgorithmService,
    private storePermissionService: StorePermissionService,
    private router: Router,
    private reviewService: StoreReviewService,
    private storeUserService: StoreUserService
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
    const store = this.chosenStoreService.store$.value;
    if (!store) {
      return;
    }
    this.algorithm = await this.algorithmService.getAlgorithm(store.url, this.algoID);
    this.reviewers = await this.storeUserService.getUsers(store.url, { can_review: true });
    this.reviews = await this.reviewService.getReviews(store.url, { algorithm_id: this.algoID });

    this.isLoading = false;
  }

  isReviewFinished(review: StoreReview): boolean {
    return review.status === ReviewStatus.Approved || review.status === ReviewStatus.Rejected || review.status === ReviewStatus.Replaced;
  }
}
