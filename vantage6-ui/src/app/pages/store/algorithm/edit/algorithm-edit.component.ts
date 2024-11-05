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

@Component({
  selector: 'app-algorithm-edit',
  templateUrl: './algorithm-edit.component.html',
  styleUrl: './algorithm-edit.component.scss'
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
    this.algorithm = await this.algorithmService.getAlgorithm(chosenStore.url, this.id);

    // parse algorithm to form
    this.algorithmForm = {
      name: this.algorithm.name,
      description: this.algorithm.description,
      partitioning: this.algorithm.partitioning,
      image: this.algorithm.image,
      vantage6_version: this.algorithm.vantage6_version,
      code_url: this.algorithm.code_url,
      documentation_url: this.algorithm.documentation_url,
      functions: this.algorithm.functions.map((func) => {
        return {
          name: func.name,
          display_name: func.display_name,
          description: func.description,
          type: func.type,
          arguments: func.arguments.map((arg) => {
            return {
              name: arg.name,
              display_name: arg.display_name,
              type: arg.type,
              description: arg.description
            };
          }),
          databases: func.databases.map((db) => {
            return {
              name: db.name,
              description: db.description
            };
          }),
          ui_visualizations: func.ui_visualizations.map((vis) => {
            return {
              name: vis.name,
              description: vis.description,
              type: vis.type,
              schema: vis.schema
            };
          })
        };
      })
    };

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
