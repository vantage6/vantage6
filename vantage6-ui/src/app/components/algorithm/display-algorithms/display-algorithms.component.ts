import { Component, Input } from '@angular/core';
import { Router } from '@angular/router';
import { Algorithm, AlgorithmStatus } from 'src/app/models/api/algorithm.model';
import { routePaths } from 'src/app/routes';
import { NgFor, TitleCasePipe } from '@angular/common';
import { MatCard, MatCardContent, MatCardFooter, MatCardHeader, MatCardTitle, MatCardTitleGroup } from "@angular/material/card";
import { MatChip, MatChipSet } from "@angular/material/chips";
import { MatRipple } from "@angular/material/core";

@Component({
    selector: 'app-display-algorithms',
    templateUrl: './display-algorithms.component.html',
    styleUrl: './display-algorithms.component.scss',
  imports: [NgFor, MatCard, MatCardHeader, MatCardFooter, MatCardContent, MatChipSet, MatChip, MatCardTitle, MatCardTitleGroup, TitleCasePipe, MatRipple]
})
export class DisplayAlgorithmsComponent {
  @Input() algorithms: Algorithm[] = [];
  @Input() routeOnClick: string = '';
  @Input() showStatus: boolean = false;
  routePaths = routePaths;

  constructor(private router: Router) {}

  handleAlgorithmClick(algorithm: Algorithm) {
    if (this.routeOnClick.startsWith('/analyze')) {
      this.router.navigate([this.routeOnClick, algorithm.id, algorithm.algorithm_store_id]);
    } else {
      this.router.navigate([this.routeOnClick, algorithm.id]);
    }
  }

  getKeywords(algorithm: Algorithm): string[] {
    const keywords = [];
    keywords.push(algorithm.partitioning);
    keywords.push(`v${algorithm.vantage6_version}`);

    return keywords;
  }

  getStatusClass(status: AlgorithmStatus): string {
    switch (status) {
      case AlgorithmStatus.Approved:
        return 'status-badge-approved';
      case AlgorithmStatus.Rejected:
        return 'status-badge-rejected';
      case AlgorithmStatus.Removed || AlgorithmStatus.Replaced:
        return 'status-badge-removed';
      default:
        return 'status-badge-pending';
    }

  }

}
