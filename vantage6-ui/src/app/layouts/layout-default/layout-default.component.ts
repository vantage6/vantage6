import { AfterViewInit, Component, OnDestroy, ViewChild } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { MatSidenav, MatSidenavContainer, MatSidenavContent } from '@angular/material/sidenav';
import { Subject, combineLatest, delay, filter, takeUntil } from 'rxjs';
import { routePaths } from 'src/app/routes';
import { NavigationLink, NavigationLinkType } from 'src/app/models/application/navigation-link.model';
import { OperationType, ResourceType, ScopeType, StoreResourceType } from 'src/app/models/api/rule.model';
import { ActivatedRoute, NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { MatToolbar } from '@angular/material/toolbar';
import { NgIf, NgFor, NgClass, AsyncPipe } from '@angular/common';
import { MatIconButton, MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatMenuTrigger, MatMenu, MatMenuItem } from '@angular/material/menu';
import { MatNavList, MatListItem, MatListItemIcon } from '@angular/material/list';
import { MatDivider } from '@angular/material/divider';
import { BreadcrumbsComponent } from '../../components/breadcrumbs/breadcrumbs.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { LoginLogoutService } from 'src/app/services/logout.service';
import { environment } from 'src/environments/environment';
import { KeycloakUserService } from 'src/app/services/keycloak-user.service';

@Component({
  selector: 'app-layout-default',
  templateUrl: './layout-default.component.html',
  styleUrls: ['./layout-default.component.scss'],
  imports: [
    MatToolbar,
    NgIf,
    MatIconButton,
    MatIcon,
    MatButton,
    MatMenuTrigger,
    MatMenu,
    MatMenuItem,
    RouterLink,
    MatSidenavContainer,
    MatSidenav,
    MatNavList,
    NgFor,
    MatListItem,
    MatListItemIcon,
    NgClass,
    RouterLinkActive,
    MatSidenavContent,
    BreadcrumbsComponent,
    MatCard,
    MatCardContent,
    RouterOutlet,
    AsyncPipe,
    TranslateModule,
    MatDivider
  ]
})
export class LayoutDefaultComponent implements AfterViewInit, OnDestroy {
  destroy$ = new Subject();
  routes = routePaths;

  hideSideMenu = false;
  navigationLinks: NavigationLink[] = [];
  isAdministration: boolean = false;
  isAnalyze: boolean = false;
  isInStore: boolean = false;
  hideMenu: boolean = false;
  username: string = '';
  showAdminSubmenu = false;
  canEditOwnUser = false;
  userId: number | undefined;

  @ViewChild(MatSidenav)
  sideNav!: MatSidenav;

  constructor(
    public router: Router,
    route: ActivatedRoute,
    private breakpointObserver: BreakpointObserver,
    private loginLogoutService: LoginLogoutService,
    public chosenCollaborationService: ChosenCollaborationService,
    public chosenStoreService: ChosenStoreService,
    private permissionService: PermissionService,
    private translateService: TranslateService,
    private storePermissionService: StorePermissionService,
    private keycloakUserService: KeycloakUserService
  ) {
    router.events.pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd)).subscribe((event) => {
      this.isAdministration = event.url.startsWith('/admin');
      this.isAnalyze = event.url.startsWith('/analyze');
      this.isInStore = event.url.startsWith('/store');

      this.hideMenu = route.snapshot.data?.['hideMenu'] || false;

      // ensure permissions are initialized before setting navigation links
      const serverPermissionInit = this.permissionService.isInitialized();
      const chosenStore = this.chosenStoreService.getCurrentStore();
      const storePermissionInit = this.storePermissionService.isInitialized();
      combineLatest([serverPermissionInit, chosenStore, storePermissionInit])
        .pipe(takeUntil(this.destroy$))
        .subscribe(([serverPermInit, chosenStore, storePermInit]) => {
          if (serverPermInit && (chosenStore === null || storePermInit)) {
            this.setNavigationLinks();
            this.canEditOwnUser = this.permissionService.isAllowed(ScopeType.OWN, ResourceType.USER, OperationType.EDIT);
            this.userId = this.permissionService.activeUser?.id;
          }
        });
    });
    this.getUserFromKeycloak();
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

  getUserFromKeycloak() {
    this.keycloakUserService.getUserProfile().then((userProfile) => {
      this.username = userProfile?.username || '';
    });
  }

  goToKeycloakAccount() {
    window.open(environment.auth_url + '/realms/' + environment.keycloak_realm + '/account', '_blank');
  }

  changePassword() {
    window.open(environment.auth_url + '/realms/' + environment.keycloak_realm + '/account/account-security/signing-in', '_blank');
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

    // store menu
    const storeLink = this.getStoreLink();
    if (storeLink.submenus) {
      newLinks.push(storeLink);
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
    this.loginLogoutService.logout();
  }

  private getAnalyzeLink(): NavigationLink {
    const link: NavigationLink = {
      route: routePaths.tasks,
      label: this.translateService.instant('links.analyze'),
      icon: 'bar_chart',
      expanded: this.isAnalyze,
      linkType: NavigationLinkType.Analyze
    };

    const submenus: NavigationLink[] = [];
    if (this.permissionService.isAllowedWithMinScope(ScopeType.COLLABORATION, ResourceType.TASK, OperationType.CREATE)) {
      submenus.push({
        route: routePaths.taskCreate,
        label: this.translateService.instant('links.new-analysis'),
        icon: 'science',
        linkType: NavigationLinkType.Analyze
      });
      submenus.push({
        route: routePaths.dataframeCreateWithoutSession,
        label: this.translateService.instant('links.new-dataframe'),
        icon: 'data_object',
        linkType: NavigationLinkType.Analyze
      });
    }
    if (this.permissionService.isAllowedWithMinScope(ScopeType.COLLABORATION, ResourceType.SESSION, OperationType.VIEW)) {
      submenus.push({
        route: routePaths.sessions,
        label: this.translateService.instant('resources.sessions'),
        icon: 'fitness_center',
        linkType: NavigationLinkType.Analyze
      });
    }
    if (this.permissionService.isAllowedWithMinScope(ScopeType.COLLABORATION, ResourceType.TASK, OperationType.VIEW)) {
      submenus.push({
        route: routePaths.tasks,
        label: this.translateService.instant('links.history'),
        icon: 'fingerprint',
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
      link.route = routePaths.chooseCollaboration;
    }
    return link;
  }

  private getStoreLink(): NavigationLink {
    const storeLink: NavigationLink = {
      route: routePaths.stores,
      label: this.translateService.instant('links.stores'),
      icon: 'shopping_cart',
      linkType: NavigationLinkType.Store,
      expanded: this.isInStore
    };

    // store submenus
    const storeSubmenus: NavigationLink[] = [];
    // we can only view stores if we have the permissions to view collaborations
    if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.COLLABORATION, OperationType.VIEW)) {
      // overview
      storeSubmenus.push({
        route: routePaths.store,
        label: this.translateService.instant('general.overview'),
        icon: 'store',
        linkType: NavigationLinkType.Store
      });
      // algorithms
      if (this.storePermissionService.canViewAlgorithms) {
        storeSubmenus.push({
          route: routePaths.algorithmManage,
          label: this.translateService.instant('links.algorithms-approved'),
          icon: 'memory',
          linkType: NavigationLinkType.Store
        });
      }
      // algorithms in review - note that explicit permission is required to view this
      // page, whereas the page with approved algorithms may be open to the public,
      // depending on the policies
      if (this.storePermissionService.isAllowed(StoreResourceType.ALGORITHM, OperationType.VIEW)) {
        storeSubmenus.push({
          route: routePaths.myPendingAlgorithms,
          label: this.translateService.instant('links.pending-algorithms'),
          icon: 'hourglass_top',
          linkType: NavigationLinkType.Store
        });
      }
      // same goes for list of old algorithms
      if (this.storePermissionService.isAllowed(StoreResourceType.ALGORITHM, OperationType.VIEW)) {
        storeSubmenus.push({
          route: routePaths.algorithmsOld,
          label: this.translateService.instant('links.old-algorithms'),
          icon: 'history',
          linkType: NavigationLinkType.Store
        });
      }

      // store users
      if (this.storePermissionService.isAllowed(StoreResourceType.USER, OperationType.VIEW)) {
        storeSubmenus.push({
          route: routePaths.storeUsers,
          label: this.translateService.instant('resources.users'),
          icon: 'people',
          linkType: NavigationLinkType.Store
        });
      }
      // store roles
      if (this.storePermissionService.isAllowed(StoreResourceType.ROLE, OperationType.VIEW)) {
        storeSubmenus.push({
          route: routePaths.storeRoles,
          label: this.translateService.instant('resources.roles'),
          icon: 'groups',
          linkType: NavigationLinkType.Store
        });
      }
    }
    if (storeSubmenus.length > 0) {
      storeLink.submenus = storeSubmenus;
      storeLink.route = storeSubmenus[0].route;
    }
    // if store has not been chosen yet, link to that page
    if (!this.chosenStoreService.store$.value) {
      storeLink.route = routePaths.stores;
    }
    return storeLink;
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
    //Users
    if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.USER, OperationType.VIEW)) {
      adminSubmenus.push({
        route: routePaths.users,
        label: this.translateService.instant('resources.users'),
        icon: 'people',
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
    //Nodes
    if (this.permissionService.isAllowedWithMinScope(ScopeType.ORGANIZATION, ResourceType.NODE, OperationType.VIEW)) {
      adminSubmenus.push({
        route: routePaths.nodes,
        label: this.translateService.instant('resources.nodes'),
        icon: 'data_object',
        linkType: NavigationLinkType.Admin
      });
    }
    if (adminSubmenus.length > 0) {
      adminLink.submenus = adminSubmenus;
      adminLink.route = adminSubmenus[0].route;
    }
    return adminLink;
  }
}
