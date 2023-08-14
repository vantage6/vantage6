import { AfterViewInit, Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { MatSidenav } from '@angular/material/sidenav';
import { Subject, delay, filter, takeUntil } from 'rxjs';
import { routePaths } from 'src/app/routes';
import { NavigationLink } from 'src/app/models/application/navigation-link.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { AuthService } from 'src/app/services/auth.service';
import { IS_ADMINISTRATION } from 'src/app/models/constants/sessionStorage';
import { NavigationEnd, Router } from '@angular/router';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';

@Component({
  selector: 'app-layout-default',
  templateUrl: './layout-default.component.html',
  styleUrls: ['./layout-default.component.scss']
})
export class LayoutDefaultComponent implements OnInit, AfterViewInit, OnDestroy {
  destroy$ = new Subject();
  routes = routePaths;

  hideSideMenu = false;
  navigationLinks: NavigationLink[] = [];
  isAdministration: boolean = false;
  isStartPage: boolean = false;

  @ViewChild(MatSidenav)
  sideNav!: MatSidenav;

  constructor(
    private router: Router,
    private breakpointObserver: BreakpointObserver,
    private authService: AuthService,
    public chosenCollaborationService: ChosenCollaborationService
  ) {
    router.events.pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd)).subscribe((event) => {
      this.isStartPage = event.url === `/${routePaths.start}`;
      this.setNavigationLinks();
    });
  }

  ngOnInit(): void {
    const isAdministration = sessionStorage.getItem(IS_ADMINISTRATION);
    this.isAdministration = isAdministration === 'true';
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

  handleAdministrationToggle() {
    this.isAdministration = !this.isAdministration;
    sessionStorage.setItem(IS_ADMINISTRATION, String(this.isAdministration));
    if (this.isAdministration) {
      this.router.navigate([routePaths.homeAdministration]);
    } else {
      this.router.navigate([routePaths.home]);
    }
  }

  private setNavigationLinks() {
    if (this.isStartPage) {
      this.navigationLinks = [];
      return;
    }

    const newLinks: NavigationLink[] = [];

    if (this.isAdministration) {
      newLinks.push({ route: routePaths.homeAdministration, label: 'Home', icon: 'home', shouldBeExact: true });
      if (this.authService.hasResourceInScope(ResourceType.ORGANIZATION, ScopeType.GLOBAL)) {
        newLinks.push({ route: routePaths.organization, label: 'Organization', icon: 'location_city' });
      }
    } else {
      newLinks.push({ route: routePaths.home, label: 'Home', icon: 'home', shouldBeExact: true });
      if (this.authService.isOperationAllowed(ResourceType.TASK, ScopeType.GLOBAL, OperationType.CREATE)) {
        newLinks.push({ route: routePaths.task, label: 'Task', icon: 'science' });
      }
    }

    this.navigationLinks = newLinks;
  }
}
