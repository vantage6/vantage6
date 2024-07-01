import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { Subject, takeUntil } from 'rxjs';
import { Algorithm, AlgorithmFunction, AlgorithmStatus } from 'src/app/models/api/algorithm.model';
import { OperationType, StoreResourceType } from 'src/app/models/api/rule.model';
import { Visualization } from 'src/app/models/api/visualization.model';
import { routePaths } from 'src/app/routes';
import { StorePermissionService } from 'src/app/services/store-permission.service';

@Component({
  selector: 'app-display-algorithm',
  templateUrl: './display-algorithm.component.html',
  styleUrl: './display-algorithm.component.scss'
})
export class DisplayAlgorithmComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() algorithm: Algorithm | undefined;
  destroy$ = new Subject<void>();

  routes = routePaths;
  algorithmStatus = AlgorithmStatus;

  selectedFunction?: AlgorithmFunction;
  canAssignReviewers: boolean = false;
  canViewReviews: boolean = false;

  constructor(private storePermissionService: StorePermissionService) {}

  ngOnInit(): void {
    this.storePermissionService.initialized$.pipe(takeUntil(this.destroy$)).subscribe((initialized) => {
      if (initialized) {
        this.canAssignReviewers = this.storePermissionService.isAllowed(StoreResourceType.REVIEW, OperationType.CREATE);
        this.canViewReviews = this.storePermissionService.isAllowed(StoreResourceType.REVIEW, OperationType.VIEW);
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
  }

  selectFunction(functionId: number): void {
    this.selectedFunction = this.algorithm?.functions.find((func: AlgorithmFunction) => func.id === functionId);
  }

  getVisualizationSchemaAsText(vis: Visualization): string {
    return JSON.stringify(vis.schema);
  }

  getButtonLink(route: string, id: number | undefined): string {
    return `${route}/${id}`;
  }

  showInvalidatedAlert(): boolean {
    if (!this.algorithm) return false;
    return ![AlgorithmStatus.Approved, AlgorithmStatus.AwaitingReviewerAssignment, AlgorithmStatus.UnderReview].includes(
      this.algorithm.status
    );
  }
}
