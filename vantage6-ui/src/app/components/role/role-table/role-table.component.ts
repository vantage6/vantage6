import { AfterViewInit, Component, OnInit, ViewChild } from '@angular/core';
import { MatPaginator } from '@angular/material/paginator';
import { MatTableDataSource } from '@angular/material/table';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import {
  EMPTY_ORGANIZATION,
  Organization,
} from 'src/app/interfaces/organization';
import { Role, RoleWithOrg } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { EMPTY_USER, User } from 'src/app/interfaces/user';
import { UtilsService } from 'src/app/services/common/utils.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { ResType } from 'src/app/shared/enum';
import { parseId } from 'src/app/shared/utils';
import {
  animate,
  state,
  style,
  transition,
  trigger,
} from '@angular/animations';

@Component({
  selector: 'app-role-table',
  templateUrl: './role-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './role-table.component.scss',
  ],
  animations: [
    trigger('detailExpand', [
      state(
        'void',
        style({ height: '0px', minHeight: '0', visibility: 'hidden' })
      ),
      state('*', style({ height: '*', visibility: 'visible' })),
      transition('void <=> *', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
})
export class RoleTableComponent implements OnInit, AfterViewInit {
  loggedin_user: User = EMPTY_USER;
  route_org_id: number | null = null;
  single_org: boolean = false;
  rules: Rule[] = [];
  roles: RoleWithOrg[] = [];
  organizations: Organization[] = [];
  displayedColumns: string[] = ['name', 'organization', 'descr'];
  data = new MatTableDataSource<RoleWithOrg>(this.roles);

  @ViewChild(MatPaginator) paginator: MatPaginator;

  isExpansionDetailRow = (index: any, row: any) =>
    row.hasOwnProperty('detailRow');

  constructor(
    private activatedRoute: ActivatedRoute,
    private userPermission: UserPermissionService,
    private utilsService: UtilsService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    private orgDataService: OrgDataService
  ) {}

  ngOnInit(): void {
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) {
        this.init();
      }
    });
  }

  ngAfterViewInit() {
    this.data.paginator = this.paginator;
  }

  async init(): Promise<void> {
    this.loggedin_user = this.userPermission.user;

    // get rules
    (await this.ruleDataService.list()).subscribe((rules) => {
      this.rules = rules;
    });

    // get organizations
    (await this.orgDataService.list()).subscribe((orgs) => {
      this.organizations = orgs;
    });

    this.activatedRoute.paramMap.subscribe((params: any) => {
      let org_id = parseId(params.get('org_id'));
      if (isNaN(org_id)) {
        this.single_org = false;
        this.route_org_id = null;
      } else {
        this.single_org = true;
        this.route_org_id = org_id;
      }
      this.setup();
    });
  }

  async setup() {
    await this.setRoles();

    await this.addOrganizationsToRoles();
    console.log(this.roles);

    this.data.data = this.roles;
  }

  private async setRoles() {
    if (this.single_org) {
      this.roles = await this.roleDataService.org_list(
        this.route_org_id as number,
        this.rules
      );
    } else {
      (await this.roleDataService.list(this.rules)).subscribe(
        (roles: Role[]) => {
          this.roles = roles;
        }
      );
    }
    console.log(this.roles);
  }

  private async addOrganizationsToRoles() {
    for (let role of this.roles) {
      for (let org of this.organizations) {
        if (org.id === role.organization_id) {
          role.organization = org;
          console.log(role);
          break;
        }
      }
    }
  }

  getRoleOrgName(role: RoleWithOrg): string {
    return role.organization ? role.organization.name : 'any';
  }

  // TODO make sure this is implemented -- but not here: a similar function
  // is already present in the RoleViewComponent
  deleteRole(role: Role) {}
}
