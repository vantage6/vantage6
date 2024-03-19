import { Component, OnDestroy } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { Subject, filter, takeUntil } from 'rxjs';

@Component({
  selector: 'app-breadcrumbs',
  templateUrl: './breadcrumbs.component.html',
  styleUrls: ['./breadcrumbs.component.scss']
})
export class BreadcrumbsComponent implements OnDestroy {
  destroy$ = new Subject();

  homeCrumb: string[] = [];
  crumbs: string[][] = [];

  constructor(router: Router, route: ActivatedRoute) {
    router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        takeUntil(this.destroy$)
      )
      .subscribe(() => {
        this.crumbs = [];
        this.homeCrumb = route.snapshot.data?.['crumb'] || [];
        this.crumbs = route.snapshot.children[0].data?.['crumbs'] || [];
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }
}
