import {Component, HostBinding, OnDestroy, OnInit} from '@angular/core';
import {Subject} from 'rxjs';
import {Algorithm} from 'src/app/models/api/algorithm.model';
import {routePaths} from 'src/app/routes';
import {AlgorithmService} from 'src/app/services/algorithm.service';
import {PageHeaderComponent} from '../../../../components/page-header/page-header.component';
import {NgIf} from '@angular/common';
import {MatButton} from '@angular/material/button';
import {RouterLink} from '@angular/router';
import {MatIcon} from '@angular/material/icon';
import {
  DisplayAlgorithmsComponent
} from '../../../../components/algorithm/display-algorithms/display-algorithms.component';
import {MatCard, MatCardContent} from '@angular/material/card';
import {MatProgressSpinner} from '@angular/material/progress-spinner';
import {TranslateModule} from '@ngx-translate/core';

@Component({
  selector: 'app-algorithm-list',
  templateUrl: './algorithm-list-public.component.html',
  styleUrl: './algorithm-list-public.component.scss',
  imports: [
    PageHeaderComponent,
    NgIf,
    MatButton,
    RouterLink,
    MatIcon,
    DisplayAlgorithmsComponent,
    MatCard,
    MatCardContent,
    MatProgressSpinner,
    TranslateModule
  ]
})
export class AlgorithmListPublicComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  isLoading = true;
  routePaths = routePaths;
  destroy$ = new Subject<void>();
  routes = routePaths;

  algorithms: Algorithm[] = [];

  canAddAlgorithm = false;

  constructor(
    private algorithmService: AlgorithmService
  ) {
  }

  async ngOnInit() {
    this.algorithms = await this.algorithmService.getAlgorithmsForCommunityStore();
    console.log("algorithms", this.algorithms);
    this.isLoading = false;
  }

  ngOnDestroy(): void {
    this.destroy$.next();
  }
}
