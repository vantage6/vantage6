import { NgIf } from '@angular/common';
import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { Subject, takeUntil } from 'rxjs';
import { routePaths } from 'src/app/routes';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { PageHeaderComponent } from 'src/app/components/page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatButton } from '@angular/material/button';
import { MatCardHeader } from '@angular/material/card';
import { MatCardTitle } from '@angular/material/card';
import { Router } from '@angular/router';
import { Algorithm, AlgorithmForm } from 'src/app/models/api/algorithm.model';
import { convertAlgorithmToAlgorithmForm } from '../helpers';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { ConfirmDialogOption } from 'src/app/models/application/confirmDialog.model';

@Component({
  selector: 'app-algorithm-update-image',
  templateUrl: './algorithm-update-image.component.html',
  styleUrl: './algorithm-update-image.component.scss',
  imports: [
    PageHeaderComponent,
    NgIf,
    MatCard,
    MatCardContent,
    MatProgressSpinner,
    TranslateModule,
    ReactiveFormsModule,
    MatFormField,
    MatInput,
    MatButton,
    MatCardHeader,
    MatLabel,
    MatCardTitle
  ]
})
export class AlgorithmUpdateImageComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id: string = '';
  destroy$ = new Subject<void>();
  routes = routePaths;

  algorithm?: Algorithm;
  isLoading = true;
  isSubmitting = false;
  algorithmForm?: AlgorithmForm;

  form = this.fb.nonNullable.group({
    image: ['', [Validators.required]]
  });

  constructor(
    private dialog: MatDialog,
    private translateService: TranslateService,
    private fb: FormBuilder,
    private algorithmService: AlgorithmService,
    private chosenStoreService: ChosenStoreService,
    private storePermissionService: StorePermissionService,
    private router: Router
  ) {}

  ngOnInit(): void {
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

    this.algorithm = await this.algorithmService.getAlgorithm(chosenStore, this.id);
    this.form.patchValue({
      image: this.algorithm?.image || ''
    });

    this.algorithmForm = convertAlgorithmToAlgorithmForm(this.algorithm);
    this.isLoading = false;
  }

  async handleSubmit(): Promise<void> {
    if (!this.algorithmForm || !this.form.value.image) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('algorithm-update-image.confirm-dialog.title'),
        content: this.translateService.instant('algorithm-update-image.confirm-dialog.content'),
        confirmButtonText: this.translateService.instant('general.submit'),
        confirmButtonType: 'primary'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === ConfirmDialogOption.PRIMARY) {
          if (!this.algorithmForm || !this.form.value.image) return;
          this.algorithmForm.image = this.form.value.image;
          const result = await this.algorithmService.createAlgorithm(this.algorithmForm);
          if (result?.id) {
            this.router.navigate([routePaths.algorithmManage, result?.id]);
          }
        }
      });
  }

  handleCancel(): void {
    this.router.navigate([routePaths.algorithmManage, this.id]);
  }
}
