import { AfterViewInit, Component, OnDestroy, ViewChild } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { MatSidenav } from '@angular/material/sidenav';
import { Subject, delay, takeUntil } from 'rxjs';
import { routePaths } from 'src/app/routes';

@Component({
  selector: 'app-layout-default',
  templateUrl: './layout-default.component.html',
  styleUrls: ['./layout-default.component.scss']
})
export class LayoutDefaultComponent implements AfterViewInit, OnDestroy {
  destroy$ = new Subject();
  hideSideMenu = false;
  routes = routePaths;

  @ViewChild(MatSidenav)
  sideNav!: MatSidenav;

  constructor(private breakpointObserver: BreakpointObserver) {}

  ngAfterViewInit(): void {
    this.breakpointObserver
      .observe([Breakpoints.XSmall])
      .pipe(takeUntil(this.destroy$), delay(1))
      .subscribe((result) => {
        this.hideSideMenu = result.matches;
        if (!this.hideSideMenu) {
          this.sideNav?.open();
        } else {
          this.sideNav?.close();
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }
}
