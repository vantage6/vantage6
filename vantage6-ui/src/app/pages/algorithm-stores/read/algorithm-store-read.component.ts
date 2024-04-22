import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore, AlgorithmStoreLazyProperties } from 'src/app/models/api/algorithmStore.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmStoreService } from 'src/app/services/algorithm-store.service';
import { AlgorithmService } from 'src/app/services/algorithm.service';

@Component({
  selector: 'app-algorithm-store-read',
  templateUrl: './algorithm-store-read.component.html',
  styleUrl: './algorithm-store-read.component.scss'
})
export class AlgorithmStoreReadComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';
  routePaths = routePaths;

  algorithmStore?: AlgorithmStore;
  algorithms?: Algorithm[];
  isLoading = true;
  collaborationTable?: TableData;

  constructor(
    private algorithmStoreService: AlgorithmStoreService,
    private algorithmService: AlgorithmService,
    private translateService: TranslateService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.isLoading = false;
  }

  private async initData(): Promise<void> {
    this.algorithmStore = await this.algorithmStoreService.getAlgorithmStore(this.id, [AlgorithmStoreLazyProperties.Collaborations]);
    if (!this.algorithmStore) return;

    if (this.algorithmStore.collaborations) {
      this.collaborationTable = {
        columns: [{ id: 'name', label: this.translateService.instant('general.name') }],
        rows: this.algorithmStore?.collaborations.map((collab) => ({
          id: collab.id.toString(),
          columnData: {
            name: collab.name
          }
        }))
      };
    }

    // collect algorithms
    this.algorithms = await this.algorithmService.getAlgorithmsForAlgorithmStore(this.algorithmStore);
  }
}
