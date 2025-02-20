import { Component, Input } from '@angular/core';
import { Router } from '@angular/router';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { routePaths } from 'src/app/routes';
import { NgFor } from '@angular/common';
import { MatButton } from '@angular/material/button';

@Component({
    selector: 'app-display-algorithms',
    templateUrl: './display-algorithms.component.html',
    styleUrl: './display-algorithms.component.scss',
    imports: [NgFor, MatButton]
})
export class DisplayAlgorithmsComponent {
  @Input() algorithms: Algorithm[] = [];
  @Input() routeOnClick: string = '';
  routePaths = routePaths;

  constructor(private router: Router) {}

  handleAlgorithmClick(algorithm: Algorithm) {
    if (this.routeOnClick.startsWith('/analyze')) {
      this.router.navigate([this.routeOnClick, algorithm.id, algorithm.algorithm_store_id]);
    } else {
      this.router.navigate([this.routeOnClick, algorithm.id]);
    }
  }
}
