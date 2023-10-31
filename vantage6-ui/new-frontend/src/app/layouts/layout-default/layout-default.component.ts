import { AfterViewInit, Component, OnDestroy, ViewChild } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { MatSidenav } from '@angular/material/sidenav';
import { Subject, delay, filter, takeUntil } from 'rxjs';
import { routePaths } from 'src/app/routes';
import { NavigationLink } from 'src/app/models/application/navigation-link.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { AuthService } from 'src/app/services/auth.service';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';

@Component({
  selector: 'app-layout-default',
  templateUrl: './layout-default.component.html',
  styleUrls: ['./layout-default.component.scss']
})
export class LayoutDefaultComponent implements AfterViewInit, OnDestroy {
  destroy$ = new Subject();
  routes = routePaths;

  hideSideMenu = false;
  navigationLinks: NavigationLink[] = [];
  isAdministration: boolean = false;
  isStartPage: boolean = false;
  hideMenu: boolean = false;

  @ViewChild(MatSidenav)
  sideNav!: MatSidenav;

  constructor(
    private router: Router,
    route: ActivatedRoute,
    private breakpointObserver: BreakpointObserver,
    private authService: AuthService,
    public chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService
  ) {
    router.events.pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd)).subscribe((event) => {
      this.isStartPage = event.url.startsWith(routePaths.start);
      this.isAdministration = event.url.startsWith(routePaths.adminHome);

      this.hideMenu = route.snapshot.data?.['hideMenu'] || false;
      this.setNavigationLinks();
    });
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

  handleToggleAdmin(): string {
    if (this.isAdministration && this.chosenCollaborationService.collaboration$.value) {
      return routePaths.home;
    } else if (this.isAdministration) {
      return routePaths.start;
    } else {
      return routePaths.adminHome;
    }
  }

  private setNavigationLinks() {
    if (this.isStartPage || this.hideMenu) {
      this.navigationLinks = [];
      return;
    }

    const newLinks: NavigationLink[] = [];

    if (this.isAdministration) {
      //Home
      newLinks.push({ route: routePaths.adminHome, label: 'Home', icon: 'home', shouldBeExact: true });
      //Organizations
      if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.ORGANIZATION, OperationType.VIEW)) {
        newLinks.push({ route: routePaths.organizations, label: 'Organizations', icon: 'location_city' });
      }
      //Collaborations
      if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.COLLABORATION, OperationType.VIEW)) {
        newLinks.push({ route: routePaths.collaborations, label: 'Collaborations', icon: 'train' });
      }
      //Users
      if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.USER, OperationType.VIEW)) {
        newLinks.push({ route: routePaths.users, label: 'Users', icon: 'people' });
      }
      //Nodes
      if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.NODE, OperationType.VIEW)) {
        newLinks.push({ route: routePaths.nodes, label: 'Nodes', icon: 'data_object' });
      }
    } else {
      //Home
      newLinks.push({ route: routePaths.home, label: 'Home', icon: 'home', shouldBeExact: true });
      //Tasks
      if (this.permissionService.isAllowedWithMinScope(ScopeType.COLLABORATION, ResourceType.TASK, OperationType.VIEW)) {
        newLinks.push({ route: routePaths.tasks, label: 'Tasks', icon: 'science' });
      }
    }

    this.navigationLinks = newLinks;
  }

  handleLogout() {
    this.authService.logout();
    this.router.navigate([routePaths.login]);
  }
}
