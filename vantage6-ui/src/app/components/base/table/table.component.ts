import { AfterViewInit, Component, OnInit, ViewChild } from '@angular/core';
import { MatPaginator } from '@angular/material/paginator';
import { MatTableDataSource } from '@angular/material/table';
import { MatSort } from '@angular/material/sort';
import {
  animate,
  state,
  style,
  transition,
  trigger,
} from '@angular/animations';
import { Resource, ResourceWithOrg } from 'src/app/shared/types';
import { Organization } from 'src/app/interfaces/organization';
import { parseId, removeMatchedIdFromArray } from 'src/app/shared/utils';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { EMPTY_USER, User } from 'src/app/interfaces/user';

@Component({
  selector: 'app-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss'],
  animations: [
    trigger('detailExpand', [
      state(
        'void',
        style({ height: '0px', minHeight: '0', visibility: 'hidden' })
      ),
      state('*', style({ height: '*', visibility: 'visible' })),
      transition('void <=> *', animate('125ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
})
export abstract class TableComponent implements OnInit, AfterViewInit {
  loggedin_user: User = EMPTY_USER;
  organizations: Organization[] = [];
  current_organization: Organization | null = null;
  route_org_id: number | null = null;
  resources: Resource[] = [];

  public dataSource = new MatTableDataSource<Resource>();

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  isExpansionDetailRow = (index: any, row: any) =>
    row.hasOwnProperty('detailRow');

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService
  ) {}

  ngOnInit(): void {
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) {
        this.loggedin_user = this.userPermission.user;
        this.init();
      }
    });
  }

  ngAfterViewInit() {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  protected abstract init(): void;
  protected abstract setResources(): void;

  async setup() {
    await this.setResources();

    await this.addOrganizationsToResources();

    this.dataSource.data = this.resources;
  }

  async readRoute() {
    this.activatedRoute.paramMap.subscribe((params: any) => {
      let org_id = parseId(params.get('org_id'));
      if (isNaN(org_id)) {
        this.route_org_id = null;
        this.current_organization = null;
      } else {
        this.route_org_id = org_id;
        this.setCurrentOrganization();
      }
      this.setup();
    });
  }

  protected setCurrentOrganization(): void {
    for (let org of this.organizations) {
      if (org.id === this.route_org_id) {
        this.current_organization = org;
        break;
      }
    }
  }

  protected async addOrganizationsToResources() {
    for (let r of this.resources as ResourceWithOrg[]) {
      for (let org of this.organizations) {
        if (org.id === r.organization_id) {
          r.organization = org;
          break;
        }
      }
    }
  }

  getOrgNameDropdown(): string {
    return this.current_organization ? this.current_organization.name : 'All';
  }

  getOrgNameTable(resource: ResourceWithOrg): string {
    return resource.organization ? resource.organization.name : '- any -';
  }

  public isShowingSingleOrg(): boolean {
    return this.route_org_id !== null;
  }

  deleteResource(resource: ResourceWithOrg) {
    this.resources = removeMatchedIdFromArray(this.resources, resource.id);
    this.dataSource.data = this.resources;
  }

  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.dataSource.filter = filterValue.trim().toLowerCase();
  }
}
