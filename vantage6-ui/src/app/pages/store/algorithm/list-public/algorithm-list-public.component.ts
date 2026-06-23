import { Component, HostBinding, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { Subject } from 'rxjs';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';

import { DisplayAlgorithmsComponent } from '../../../../components/algorithm/display-algorithms/display-algorithms.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-algorithm-list-public',
  templateUrl: './algorithm-list-public.component.html',
  styleUrl: './algorithm-list-public.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [PageHeaderComponent, DisplayAlgorithmsComponent, MatCard, MatCardContent, MatProgressSpinner, TranslateModule]
})
export class AlgorithmListPublicComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  isLoading = true;
  routePaths = routePaths;
  destroy$ = new Subject<void>();
  routes = routePaths;
  algorithms: Algorithm[] = [];

  constructor(private algorithmService: AlgorithmService) {}

  async ngOnInit() {
    this.algorithms = await this.algorithmService.getAlgorithmsForCommunityStore();
    this.isLoading = false;
  }
}
