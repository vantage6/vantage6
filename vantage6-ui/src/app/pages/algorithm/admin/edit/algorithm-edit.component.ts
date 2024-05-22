import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { Algorithm, AlgorithmForm } from 'src/app/models/api/algorithm.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { FileService } from 'src/app/services/file.service';

@Component({
  selector: 'app-algorithm-edit',
  templateUrl: './algorithm-edit.component.html',
  styleUrl: './algorithm-edit.component.scss'
})
export class AlgorithmEditComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  @Input() id: string = '';

  isLoading: boolean = true;
  isSubmitting: boolean = false;
  algorithm?: Algorithm;

  constructor(
    private router: Router,
    private algorithmService: AlgorithmService,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private fileService: FileService,
    private chosenStoreService: ChosenStoreService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.isLoading = false;
  }

  private async initData(): Promise<void> {
    const chosenStore = this.chosenStoreService.store$.value;
    if (!chosenStore) return;
    this.algorithm = await this.algorithmService.getAlgorithm(chosenStore.url, this.id);
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
