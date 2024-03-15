import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { AddAlgorithmStore, AlgorithmStoreForm } from 'src/app/models/api/algorithmStore.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmStoreService } from 'src/app/services/algorithm-store.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { SnackbarService } from 'src/app/services/snackbar.service';

@Component({
  selector: 'app-add-algo-store',
  templateUrl: './add-algo-store.component.html',
  styleUrls: ['./add-algo-store.component.scss']
})
export class AddAlgoStoreComponent implements OnInit {
  id = '';
  isSubmitting = false;

  constructor(
    private dialog: MatDialog,
    private router: Router,
    private translateService: TranslateService,
    private algorithmStoreService: AlgorithmStoreService,
    private snackBarService: SnackbarService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit(): Promise<void> {
    this.id = this.router.url.split('/').pop() || '';
  }

  async handleSubmit(algorithmStoreForm: AlgorithmStoreForm): Promise<void> {
    // convert form to API parameters
    const addAlgorithmStore: AddAlgorithmStore = {
      name: algorithmStoreForm.name,
      algorithm_store_url: algorithmStoreForm.algorithm_store_url,
      server_url: algorithmStoreForm.server_url
    };
    if (!algorithmStoreForm.all_collaborations) {
      addAlgorithmStore.collaboration_id = algorithmStoreForm.collaboration_id;
    }

    this.isSubmitting = true;
    try {
      await this.algorithmStoreService.addAlgorithmStore(addAlgorithmStore);
      // always refresh the chosen collaboration after adding an algorithm store
      this.chosenCollaborationService.refresh();
    } catch (error) {
      if (this.urlsContainLocalhost(addAlgorithmStore)) {
        await this.handleLocalhostAddition(addAlgorithmStore);
      }
    } finally {
      this.goToCollaboration();
    }
  }

  async handleCancel(): Promise<void> {
    this.goToCollaboration();
  }

  private async handleLocalhostAddition(algorithmStoreForm: AddAlgorithmStore): Promise<void> {
    // close the snackbar that has been opened with the warning
    this.snackBarService.dismiss();
    // for localhost additions, show a warning first
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('algorithm-store-add.localhost-dialog.title'),
        content: this.translateService.instant('algorithm-store-add.localhost-dialog.content'),
        confirmButtonText: this.translateService.instant('algorithm-store-add.localhost-dialog.confirm'),
        confirmButtonType: 'warn'
      }
    });
    const dialogResponse = await dialogRef.afterClosed().toPromise();
    if (dialogResponse === true) {
      algorithmStoreForm.force = true;
      await this.algorithmStoreService.addAlgorithmStore(algorithmStoreForm);
    }
  }

  private goToCollaboration(): void {
    this.router.navigate([routePaths.collaboration, this.id]);
  }

  private urlsContainLocalhost(addAlgorithmStore: AddAlgorithmStore): boolean {
    return (
      addAlgorithmStore.algorithm_store_url.includes('localhost') ||
      addAlgorithmStore.server_url.includes('localhost') ||
      addAlgorithmStore.algorithm_store_url.includes('127.0.0.1') ||
      addAlgorithmStore.server_url.includes('127.0.0.1')
    );
  }
}
