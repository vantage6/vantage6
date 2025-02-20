import { Component, HostBinding, OnInit } from '@angular/core';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatButton } from '@angular/material/button';
import { RouterLink } from '@angular/router';
import { NgIf } from '@angular/common';
import { DisplayAlgorithmsComponent } from '../../../../components/algorithm/display-algorithms/display-algorithms.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-algorithm-list',
  templateUrl: './algorithm-list-read-only.component.html',
  styleUrl: './algorithm-list-read-only.component.scss',
  standalone: true,
  imports: [
    PageHeaderComponent,
    MatButton,
    RouterLink,
    NgIf,
    DisplayAlgorithmsComponent,
    MatCard,
    MatCardContent,
    MatProgressSpinner,
    TranslateModule
  ]
})
export class AlgorithmListReadOnlyComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  isLoading = true;
  routePaths = routePaths;

  algorithms: Algorithm[] = [];
  stores: AlgorithmStore[] = [];

  constructor(private algorithmService: AlgorithmService) {}

  async ngOnInit() {
    await this.initData();
    this.isLoading = false;
  }

  private async initData(): Promise<void> {
    this.algorithms = await this.algorithmService.getAlgorithms();
  }
}
