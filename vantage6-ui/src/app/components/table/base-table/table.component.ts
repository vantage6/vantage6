import {
  animate,
  state,
  style,
  transition,
  trigger,
} from '@angular/animations';
import { SelectionModel } from '@angular/cdk/collections';
import { AfterViewInit, Component, OnInit, ViewChild } from '@angular/core';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Organization } from 'src/app/interfaces/organization';
import { EMPTY_USER, User } from 'src/app/interfaces/user';
import { ModalService } from 'src/app/services/common/modal.service';
import { Resource, ResourceWithOrg } from 'src/app/shared/types';
import {
  arrayContainsObjWithId,
  parseId,
  removeMatchedIdFromArray,
} from 'src/app/shared/utils';

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
  selection = new SelectionModel<Resource>(true, []);

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  isExpansionDetailRow = (index: any, row: any) =>
    row.hasOwnProperty('detailRow');

  sortBy(sorter: any) {
    if (!sorter) return '';
    else if (sorter instanceof String) return sorter.toLocaleLowerCase();
    else return sorter;
  }

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    protected modalService: ModalService
  ) {}

  ngOnInit(): void {
    this.modalService.openLoadingModal();

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
  protected abstract setResources(force_refresh: boolean): void;

  async setup(force_refresh: boolean = false) {
    await this.setResources(force_refresh);

    // TODO remove call when all setResources() subfunctions call this
    this.renewTable();
  }

  async renewTable(): Promise<void> {
    await this.addOrganizationsToResources();

    this.dataSource.data = this.resources;

    this.modalService.closeLoadingModal();
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

  deleteResource(resource: Resource) {
    this.resources = removeMatchedIdFromArray(this.resources, resource.id);
    this.dataSource.data = this.resources;
  }

  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.dataSource.filter = filterValue.trim().toLowerCase();
  }

  /** Whether the number of selected elements matches the total number of rows. */
  isAllSelected() {
    const numSelected = this.selection.selected.length;
    const numRows = this.dataSource.filteredData.length;
    return numSelected === numRows;
  }

  isAllOnPageSelected() {
    let page_size = this.paginator.pageSize;
    let start_idx = this.getPageStartIndex();
    let end_idx = this.getPageEndIndex(start_idx, page_size);
    return this.allSelectedInRange(start_idx, end_idx);
  }

  /** Selects all rows if they are not all selected; otherwise clear selection. */
  masterToggle() {
    this.isAllOnPageSelected()
      ? this.clearPageSelection()
      : this.selectRowsCurrentPage();
  }

  private clearPageSelection() {
    let page_size = this.paginator.pageSize;
    let start_idx = this.getPageStartIndex();
    let end_idx = this.getPageEndIndex(start_idx, page_size);
    // deselect the rows
    for (let index = start_idx; index < end_idx; index++) {
      this.selection.deselect(this.dataSource.filteredData[index]);
    }
  }

  private selectRowsCurrentPage() {
    let page_size = this.paginator.pageSize;
    let start_idx = this.getPageStartIndex();
    let end_idx = this.getPageEndIndex(start_idx, page_size);

    // select the rows
    for (let index = start_idx; index < end_idx; index++) {
      this.selection.select(this.dataSource.filteredData[index]);
    }
  }

  private getPageStartIndex(): number {
    return this.paginator.pageIndex * this.paginator.pageSize;
  }

  private getPageEndIndex(start_idx: number, page_size: number) {
    if (this.dataSource.filteredData.length > start_idx + page_size) {
      return (this.paginator.pageIndex + 1) * this.paginator.pageSize;
    } else {
      return this.dataSource.filteredData.length;
    }
  }

  private allSelectedInRange(start_idx: number, end_idx: number): boolean {
    for (let index = start_idx; index < end_idx; index++) {
      if (
        !arrayContainsObjWithId(
          this.dataSource.filteredData[index].id,
          this.selection.selected
        )
      ) {
        return false;
      }
    }
    return true;
  }
}
