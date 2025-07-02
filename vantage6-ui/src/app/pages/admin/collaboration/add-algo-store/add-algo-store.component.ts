import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { AddAlgorithmStore, AlgorithmStoreForm } from 'src/app/models/api/algorithmStore.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmStoreService } from 'src/app/services/algorithm-store.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { environment } from 'src/environments/environment';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf } from '@angular/common';
import { MatCard, MatCardContent } from '@angular/material/card';
import { AlgorithmStoreFormComponent } from '../../../../components/forms/algorithm-store-form/algorithm-store-form.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-add-algo-store',
  templateUrl: './add-algo-store.component.html',
  styleUrls: ['./add-algo-store.component.scss'],
  imports: [PageHeaderComponent, NgIf, MatCard, MatCardContent, AlgorithmStoreFormComponent, MatProgressSpinner, TranslateModule]
})
export class AddAlgoStoreComponent implements OnInit {
  id = '';
  isSubmitting = false;

  constructor(
    private router: Router,
    private algorithmStoreService: AlgorithmStoreService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit(): Promise<void> {
    this.id = this.router.url.split('/').pop() || '';
  }

  async handleSubmit(algorithmStoreForm: AlgorithmStoreForm): Promise<void> {
    // convert form to API parameters
    const addAlgorithmStore: AddAlgorithmStore = {
      name: algorithmStoreForm.name,
      algorithm_store_url: algorithmStoreForm.algorithm_store_url
    };
    if (!algorithmStoreForm.all_collaborations) {
      addAlgorithmStore.collaboration_id = algorithmStoreForm.collaboration_id;
    }

    this.isSubmitting = true;
    try {
      await this.addAlgorithmStore(addAlgorithmStore);
    } finally {
      this.goToCollaboration();
    }
  }

  async handleCancel(): Promise<void> {
    this.goToCollaboration();
  }

  private async addAlgorithmStore(algorithmStoreForm: AddAlgorithmStore): Promise<void> {
    await this.algorithmStoreService.addAlgorithmStore(algorithmStoreForm);
    // always refresh the chosen collaboration after adding an algorithm store
    this.chosenCollaborationService.refresh();
  }

  private goToCollaboration(): void {
    this.router.navigate([routePaths.collaboration, this.id]);
  }
}
