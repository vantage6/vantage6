import { AfterViewInit, Component, OnDestroy, ViewChild } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { MatSidenav } from '@angular/material/sidenav';
import { Subject, delay, filter, takeUntil } from 'rxjs';
import { routePaths } from 'src/app/routes';
import { NavigationLink, NavigationLinkType } from 'src/app/models/application/navigation-link.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { AuthService } from 'src/app/services/auth.service';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { TokenStorageService } from 'src/app/services/token-storage.service';
import { TranslateService } from '@ngx-translate/core';

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
  isAnalyze: boolean = false;
  hideMenu: boolean = false;
  username: string = '';
  showAdminSubmenu = false;

  @ViewChild(MatSidenav)
  sideNav!: MatSidenav;

  constructor(
    public router: Router,
    route: ActivatedRoute,
    private breakpointObserver: BreakpointObserver,
    private authService: AuthService,
    public chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService,
    private tokenStorageService: TokenStorageService,
    private translateService: TranslateService
  ) {
    router.events.pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd)).subscribe((event) => {
      this.isAdministration = event.url.startsWith('/admin');
      this.isAnalyze = event.url.startsWith('/analyze');

      this.hideMenu = route.snapshot.data?.['hideMenu'] || false;

      // ensure permissions are initialized before setting navigation links
      this.permissionService
        .isInitialized()
        .pipe(takeUntil(this.destroy$))
        .subscribe((initialized) => {
          if (initialized) {
            this.setNavigationLinks();
          }
        });
    });
    this.username = this.tokenStorageService.getUsername() || '';
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

  private setNavigationLinks(): void {
    if (this.hideMenu) {
      this.navigationLinks = [];
      return;
    }

    const newLinks: NavigationLink[] = [];

    // Home
    newLinks.push({
      route: routePaths.home,
      label: this.translateService.instant('links.home'),
      icon: 'home',
      shouldBeExact: true,
      linkType: NavigationLinkType.Home
    });

    const analyzeLink = this.getAnalyzeLink();
    if (analyzeLink.submenus) {
      newLinks.push(analyzeLink);
    }

    // TODO get rid of adminHome route

    //Main admin menu
    const adminLink = this.getAdminLink();
    if (adminLink.submenus) {
      newLinks.push(this.getAdminLink());
    }

    this.navigationLinks = newLinks;
  }

  goToFirstSubmenu(link: NavigationLink): void {
    if (link.linkType === NavigationLinkType.Home) {
      this.router.navigate([link.route]);
    } else if (link.submenus && link.submenus.length > 0) {
      this.router.navigate([link.submenus[0].route]);
    }
  }

  handleLogout() {
    this.authService.logout();
    this.router.navigate([routePaths.login]);
  }

  private getAnalyzeLink(): NavigationLink {
    const link: NavigationLink = {
      route: routePaths.tasks,
      label: this.translateService.instant('links.analyze'),
      icon: 'bar_chart',
      expanded: this.isAnalyze,
      linkType: NavigationLinkType.Analyze
    };

    //Tasks
    const submenus: NavigationLink[] = [];
    if (this.permissionService.isAllowedWithMinScope(ScopeType.COLLABORATION, ResourceType.TASK, OperationType.VIEW)) {
      submenus.push({
        route: routePaths.tasks,
        label: this.translateService.instant('resources.tasks'),
        icon: 'science',
        linkType: NavigationLinkType.Analyze
      });
    }
    submenus.push({
      route: routePaths.algorithms,
      label: this.translateService.instant('resources.algorithms'),
      icon: 'memory',
      linkType: NavigationLinkType.Analyze
    });
    //Template tasks
    // if (this.permissionService.isAllowedWithMinScope(ScopeType.COLLABORATION, ResourceType.TASK, OperationType.CREATE)) {
    //   newLinks.push({ route: routePaths.templateTaskCreate, label: 'Quick tasks', icon: 'assignment' });
    // }
    if (submenus.length > 0) {
      link.submenus = submenus;
      link.route = submenus[0].route;
    }
    // if collaboration has not been chosen yet, link to that page
    if (!this.chosenCollaborationService.collaboration$.value) {
      link.route = routePaths.start;
    }
    return link;
  }

  private getAdminLink(): NavigationLink {
    const adminLink: NavigationLink = {
      route: routePaths.adminHome,
      label: this.translateService.instant('links.admin'),
      icon: 'settings',
      expanded: this.isAdministration,
      linkType: NavigationLinkType.Admin
    };

    // admin submenus
    const adminSubmenus: NavigationLink[] = [];
    //Collaborations
    if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.COLLABORATION, OperationType.VIEW)) {
      adminSubmenus.push({
        route: routePaths.collaborations,
        label: this.translateService.instant('resources.collaborations'),
        icon: 'train',
        linkType: NavigationLinkType.Admin
      });
    }
    //Organizations
    if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.ORGANIZATION, OperationType.VIEW)) {
      adminSubmenus.push({
        route: routePaths.organizations,
        label: this.translateService.instant('resources.organizations'),
        icon: 'location_city',
        linkType: NavigationLinkType.Admin
      });
    }
    //Roles
    if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.COLLABORATION, OperationType.VIEW)) {
      adminSubmenus.push({
        route: routePaths.roles,
        label: this.translateService.instant('resources.roles'),
        icon: 'groups',
        linkType: NavigationLinkType.Admin
      });
    }
    //Users
    if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.USER, OperationType.VIEW)) {
      adminSubmenus.push({
        route: routePaths.users,
        label: this.translateService.instant('resources.users'),
        icon: 'people',
        linkType: NavigationLinkType.Admin
      });
    }
    //Nodes
    if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.NODE, OperationType.VIEW)) {
      adminSubmenus.push({
        route: routePaths.nodes,
        label: this.translateService.instant('resources.nodes'),
        icon: 'data_object',
        linkType: NavigationLinkType.Admin
      });
    }
    // TODO for algorithm store, use <mat-icon> store_mall_directory</mat-icon>
    if (adminSubmenus.length > 0) {
      adminLink.submenus = adminSubmenus;
      adminLink.route = adminSubmenus[0].route;
    }
    return adminLink;
  }
}
