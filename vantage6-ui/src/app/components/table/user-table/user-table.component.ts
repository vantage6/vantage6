import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { User } from 'src/app/interfaces/user';
import { ModalService } from 'src/app/services/common/modal.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { UserDataService } from 'src/app/services/data/user-data.service';
import { TableComponent } from '../base-table/table.component';
import {
  Pagination,
  allPages,
  defaultFirstPage,
} from 'src/app/interfaces/utils';

@Component({
  selector: 'app-user-table',
  templateUrl: './user-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../table/base-table/table.component.scss',
    './user-table.component.scss',
  ],
})
export class UserTableComponent extends TableComponent implements OnInit {
  displayedColumns: string[] = [
    'id',
    'username',
    'email',
    'first_name',
    'last_name',
    'organization',
  ];

  constructor(
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private userDataService: UserDataService,
    private orgDataService: OrgDataService,
    protected modalService: ModalService
  ) {
    super(activatedRoute, userPermission, modalService, userDataService);
  }

  ngAfterViewInit(): void {
    super.ngAfterViewInit();
    this.dataSource.sortingDataAccessor = (item: any, property: any) => {
      let sorter: any;
      if (property === 'organization') {
        sorter = item.organization.name;
      } else {
        sorter = item[property];
      }
      return this.sortBy(sorter);
    };
  }

  async init(): Promise<void> {
    // get organizations
    (await this.orgDataService.list(false, allPages())).subscribe((orgs) => {
      this.organizations = orgs;
    });

    this.readRoute();
  }

  protected async setResources(force_refresh: boolean = false) {
    if (this.isShowingSingleOrg()) {
      (
        await this.userDataService.org_list(
          this.route_org_id as number,
          force_refresh,
          this.page
        )
      ).subscribe((users) => {
        this.resources = users;
        this.renewTable();
      });
    } else {
      (await this.userDataService.list(this.page, force_refresh)).subscribe(
        (users: User[]) => {
          this.resources = users;
          this.renewTable();
        }
      );
    }
  }
}
