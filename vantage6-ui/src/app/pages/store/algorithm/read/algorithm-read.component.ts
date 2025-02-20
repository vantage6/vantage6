import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { Algorithm, AlgorithmFunction, AlgorithmStatus } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { HandleConfirmDialogService } from 'src/app/services/handle-confirm-dialog.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { NgIf } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatIconButton, MatButton } from '@angular/material/button';
import { MatMenuTrigger, MatMenu, MatMenuItem } from '@angular/material/menu';
import { MatIcon } from '@angular/material/icon';
import { AlertWithButtonComponent } from '../../../../components/alerts/alert-with-button/alert-with-button.component';
import { AlertComponent } from '../../../../components/alerts/alert/alert.component';
import { DisplayAlgorithmComponent } from '../../../../components/algorithm/display-algorithm/display-algorithm.component';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
    selector: 'app-algorithm-read',
    templateUrl: './algorithm-read.component.html',
    styleUrl: './algorithm-read.component.scss',
    imports: [
        NgIf,
        PageHeaderComponent,
        MatIconButton,
        MatMenuTrigger,
        MatIcon,
        MatMenu,
        MatMenuItem,
        RouterLink,
        AlertWithButtonComponent,
        AlertComponent,
        DisplayAlgorithmComponent,
        MatCard,
        MatCardHeader,
        MatCardTitle,
        MatCardContent,
        MatButton,
        MatProgressSpinner,
        TranslateModule
    ]
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

  private async initData(): Promise<void> {
    const chosenStore = this.chosenStoreService.store$.value;
    if (!chosenStore) return;

    this.algorithm = await this.algorithmService.getAlgorithm(chosenStore.url, this.id);

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
