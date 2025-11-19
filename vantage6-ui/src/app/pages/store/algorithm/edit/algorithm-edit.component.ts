import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { Algorithm, AlgorithmForm } from 'src/app/models/api/algorithm.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { NgIf } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { AlgorithmFormComponent } from '../../../../components/forms/algorithm-form/algorithm-form.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { convertAlgorithmToAlgorithmForm } from '../helpers';

@Component({
  selector: 'app-algorithm-edit',
  templateUrl: './algorithm-edit.component.html',
  styleUrl: './algorithm-edit.component.scss',
  imports: [NgIf, PageHeaderComponent, AlgorithmFormComponent, MatCard, MatCardContent, MatProgressSpinner]
})
export class AlgorithmEditComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id: string = '';
  destroy$ = new Subject<void>();

  isLoading: boolean = true;
  isSubmitting: boolean = false;
  algorithm?: Algorithm;
  algorithmForm?: AlgorithmForm;

  constructor(
    private router: Router,
    private algorithmService: AlgorithmService,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private chosenStoreService: ChosenStoreService
  ) {}

  async ngOnInit(): Promise<void> {
    this.chosenStoreService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.initData();
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private async initData(): Promise<void> {
    const chosenStore = this.chosenStoreService.store$.value;
    if (!chosenStore) return;
    this.algorithm = await this.algorithmService.getAlgorithm(chosenStore, this.id);

    // parse algorithm to form
    this.algorithmForm = convertAlgorithmToAlgorithmForm(this.algorithm);

    this.isLoading = false;
  }

  async handleSubmit(algorithmForm: AlgorithmForm) {
    if (!this.algorithm) return;

    this.isSubmitting = true;

    const result = await this.algorithmService.editAlgorithm(this.algorithm.id.toString(), algorithmForm);
    if (result?.id) {
      this.dialog.open(MessageDialogComponent, {
        data: {
          title: this.translateService.instant('algorithm-edit.success-dialog.title'),
          message: this.translateService.instant('algorithm-edit.success-dialog.message')
        }
      });
      this.router.navigate([routePaths.algorithmManage, result.id]);
    } else {
      this.dialog.open(MessageDialogComponent, {
        data: {
          title: this.translateService.instant('algorithm-edit.error-dialog.title'),
          message: this.translateService.instant('algorithm-edit.error-dialog.message')
        }
      });
    }

    this.isSubmitting = false;
  }

  handleCancel() {
    this.router.navigate([routePaths.algorithmManage, this.id]);
  }
}
