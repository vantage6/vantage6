import { AfterViewInit, Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { MatSidenav } from '@angular/material/sidenav';
import { Subject, delay, takeUntil } from 'rxjs';
import { routePaths } from 'src/app/routes';
import { NavigationLink } from 'src/app/models/application/navigation-link.model';
import { ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { AuthService } from 'src/app/services/auth.service';

@Component({
  selector: 'app-layout-default',
  templateUrl: './layout-default.component.html',
  styleUrls: ['./layout-default.component.scss']
})
export class LayoutDefaultComponent implements OnInit, AfterViewInit, OnDestroy {
  destroy$ = new Subject();
  hideSideMenu = false;
  navigationLinks: NavigationLink[] = [];

  @ViewChild(MatSidenav)
  sideNav!: MatSidenav;

  constructor(
    private breakpointObserver: BreakpointObserver,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.navigationLinks.push({ route: routePaths.home, label: 'Home', icon: 'home', shouldBeExact: true });
    if (this.authService.hasResourceInScope(ResourceType.ORGANIZATION, ScopeType.GLOBAL)) {
      this.navigationLinks.push({ route: routePaths.organization, label: 'Organization', icon: 'location_city' });
    }
  }

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
