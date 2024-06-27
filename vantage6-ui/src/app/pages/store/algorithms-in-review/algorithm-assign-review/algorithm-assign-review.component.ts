import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { BaseCreateComponent } from 'src/app/components/admin-base/base-create/base-create.component';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { StoreReview } from 'src/app/models/api/review.model';
import { StoreUser } from 'src/app/models/api/store-user.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { PermissionService } from 'src/app/services/permission.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { StoreReviewService } from 'src/app/services/store-review.service';
import { StoreUserService } from 'src/app/services/store-user.service';

@Component({
  selector: 'app-algorithm-assign-review',
  templateUrl: './algorithm-assign-review.component.html',
  styleUrl: './algorithm-assign-review.component.scss'
})
export class AlgorithmAssignReviewComponent extends BaseCreateComponent implements OnInit, OnDestroy {
  @Input() algoID: string = '';
  destroy$ = new Subject<void>();
  isLoading: boolean = true;

  algorithm: Algorithm | null = null;
  reviewers: StoreUser[] = [];
  existing_reviews: StoreReview[] = [];

  form = this.fb.nonNullable.group({
    reviewers: [[] as StoreUser[], [Validators.required]]
  });

  constructor(
    private chosenStoreService: ChosenStoreService,
    private algorithmService: AlgorithmService,
    private storePermissionService: StorePermissionService,
    private router: Router,
    private storeUserService: StoreUserService,
    private fb: FormBuilder,
    private reviewService: StoreReviewService,
    private permissionService: PermissionService
  ) {
    super();
  }

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
    let reviewers = await this.storeUserService.getUsers(store.url, { can_review: true });
    // filter the logged in user as they cannot review their own algorithm
    const loggedInUser = this.permissionService.activeUser;
    if (loggedInUser) {
      reviewers = reviewers.filter((reviewer) => reviewer.username !== loggedInUser.username);
    }
    // also get existing reviews for this algorithm and remove those reviewers from the list as well
    this.existing_reviews = await this.reviewService.getReviews(store.url, { algorithm_id: this.algoID });
    reviewers = reviewers.filter((reviewer) => !this.existing_reviews.some((review) => review.reviewer.id === reviewer.id));

    // the remaining users are still assignable as reviewer
    this.reviewers = reviewers;
    this.isLoading = false;
  }

  async handleSubmit() {
    const store = this.chosenStoreService.store$.value;
    if (!this.form.valid || !store) {
      return;
    }
    this.isLoading = true;
    const formValue = this.form.getRawValue();
    const reviewers = formValue.reviewers.map((reviewer) => reviewer.id);

    const promises = reviewers.map(async (reviewer) => {
      const reviewCreate = {
        algorithm_id: Number(this.algoID),
        reviewer_id: reviewer
      };
      await this.reviewService.createReview(store.url, reviewCreate);
    });
    await Promise.all(promises);
    this.isLoading = false;
    this.router.navigate([routePaths.algorithmReviews]);
  }

  handleCancel() {
    this.router.navigate([routePaths.algorithmReviews]);
  }
}
