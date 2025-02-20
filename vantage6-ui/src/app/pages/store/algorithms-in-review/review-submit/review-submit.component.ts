import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { BaseEditComponent } from 'src/app/components/admin-base/base-edit/base-edit.component';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { ReviewForm, StoreReview } from 'src/app/models/api/review.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { HandleConfirmDialogService } from 'src/app/services/handle-confirm-dialog.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { StoreReviewService } from 'src/app/services/store-review.service';
import { NgIf } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatRadioGroup, MatRadioButton } from '@angular/material/radio';
import { MatButton } from '@angular/material/button';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-review-submit',
  templateUrl: './review-submit.component.html',
  styleUrl: './review-submit.component.scss',
  standalone: true,
  imports: [
    NgIf,
    PageHeaderComponent,
    MatCard,
    MatCardContent,
    ReactiveFormsModule,
    MatRadioGroup,
    MatRadioButton,
    MatButton,
    MatProgressSpinner,
    TranslateModule
  ]
})
// extends BaseEditComponent
export class ReviewSubmitComponent extends BaseEditComponent implements OnInit, OnDestroy {
  destroy$ = new Subject<void>();

  review?: StoreReview;
  store: AlgorithmStore | null = null;
  algorithm?: Algorithm;

  form = this.fb.nonNullable.group({
    approve: [false, [Validators.required]],
    comment: ['']
  });

  constructor(
    private chosenStoreService: ChosenStoreService,
    private algorithmService: AlgorithmService,
    private storePermissionService: StorePermissionService,
    private router: Router,
    private reviewService: StoreReviewService,
    private fb: FormBuilder,
    private handleConfirmDialogService: HandleConfirmDialogService,
    private translateService: TranslateService
  ) {
    super();
  }

  override async ngOnInit(): Promise<void> {
    this.storePermissionService.initialized$.pipe(takeUntil(this.destroy$)).subscribe((initialized) => {
      if (initialized) {
        this.initData();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
  }

  protected async initData(): Promise<void> {
    this.store = this.chosenStoreService.store$.value;
    if (!this.store) return;
    this.review = await this.reviewService.getReview(this.store.url, this.id);
    this.algorithm = await this.algorithmService.getAlgorithm(this.store.url, this.review?.algorithm_id.toString());
    this.isLoading = false;
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  protected async handleSubmit(_: ReviewForm): Promise<void> {
    if (!this.store || !this.review) return;

    const formValues = this.form.getRawValue();
    const isApprove = formValues.approve;
    if (isApprove) {
      this.handleApprove(formValues.comment);
    } else {
      this.handleReject(formValues.comment);
    }
  }

  protected override handleCancel(): void {
    this.review?.algorithm_id
      ? this.router.navigate([routePaths.algorithmReview, this.review?.algorithm_id])
      : this.router.navigate([routePaths.algorithmReviews]);
  }

  private async handleApprove(comment: string): Promise<void> {
    this.handleConfirmDialogService.handleConfirmDialog(
      this.translateService.instant('review-submit.approve-dialog.title'),
      this.translateService.instant('review-submit.approve-dialog.content'),
      this.translateService.instant('general.confirm'),
      'primary',
      () => {
        if (!this.store || !this.review) return;
        this.reviewService.approveReview(this.store.url, this.review.id, comment).then(() => {
          if (!this.review) return;
          this.router.navigate([routePaths.algorithmManage, this.review.algorithm_id]);
        });
      }
    );
  }

  private async handleReject(comment: string): Promise<void> {
    this.handleConfirmDialogService.handleConfirmDialog(
      this.translateService.instant('review-submit.reject-dialog.title'),
      this.translateService.instant('review-submit.reject-dialog.content'),
      this.translateService.instant('general.confirm'),
      'warn',
      () => {
        if (!this.store || !this.review) return;
        this.reviewService.rejectReview(this.store.url, this.review.id, comment).then(() => {
          if (!this.review) return;
          this.router.navigate([routePaths.algorithmManage, this.review.algorithm_id]);
        });
      }
    );
  }
}
