import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { Algorithm, AlgorithmFunction, AlgorithmStatus } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { FileService } from 'src/app/services/file.service';
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
    private fileService: FileService,
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

  downloadAlgorithmJson(): void {
    if (!this.algorithm) return;
    const filename = `${this.algorithm.name}.json`;

    // remove all nested ID fields as they should not be included in the download
    const cleanedAlgorithmRepresentation: any = { ...this.algorithm };
    delete cleanedAlgorithmRepresentation.id;
    for (const func of cleanedAlgorithmRepresentation.functions) {
      delete func.id;
      for (const param of func.arguments) {
        delete param.id;
      }
      for (const db of func.databases) {
        delete db.id;
      }
      for (const ui_vis of func.ui_visualizations) {
        delete ui_vis.id;
      }
    }

    // also remove other algorithm store properties that should not be included in the
    // download
    delete cleanedAlgorithmRepresentation.digest;
    delete cleanedAlgorithmRepresentation.status;
    delete cleanedAlgorithmRepresentation.submitted_at;
    delete cleanedAlgorithmRepresentation.approved_at;
    delete cleanedAlgorithmRepresentation.invalidated_at;

    const text = JSON.stringify(cleanedAlgorithmRepresentation, null, 2);
    this.fileService.downloadTxtFile(text, filename);
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
