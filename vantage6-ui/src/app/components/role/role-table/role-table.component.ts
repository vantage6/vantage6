import { AfterViewInit, Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Organization } from 'src/app/interfaces/organization';
import { Role, RoleWithOrg } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { EMPTY_USER, User } from 'src/app/interfaces/user';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { parseId, removeMatchedIdFromArray } from 'src/app/shared/utils';
import { TableComponent } from 'src/app/components/table/table.component';

@Component({
  selector: 'app-role-table',
  templateUrl: './role-table.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../table/table.component.scss',
    './role-table.component.scss',
  ],
})
export class RoleTableComponent
  extends TableComponent
  implements OnInit, AfterViewInit
{
  loggedin_user: User = EMPTY_USER;
  route_org_id: number | null = null;
  single_org: boolean = false;
  rules: Rule[] = [];
  roles: RoleWithOrg[] = [];
  organizations: Organization[] = [];
  current_organization: Organization | null = null;
  displayedColumns: string[] = ['name', 'organization', 'descr'];

  constructor(
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    private orgDataService: OrgDataService
  ) {
    super();
  }

  ngOnInit(): void {
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) {
        this.init();
      }
    });
  }

  ngAfterViewInit() {
    this.table_data.paginator = this.paginator;
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
        this.current_organization = null;
      } else {
        this.single_org = true;
        this.route_org_id = org_id;
        this.setCurrentOrganization();
      }
      this.setup();
    });
  }

  async setup() {
    await this.setRoles();

    await this.addOrganizationsToRoles();

    this.table_data.data = this.roles;
  }

  private setCurrentOrganization(): void {
    for (let org of this.organizations) {
      if (org.id === this.route_org_id) {
        this.current_organization = org;
        break;
      }
    }
  }

  getOrgName(): string {
    return this.current_organization ? this.current_organization.name : 'All';
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
  }

  private async addOrganizationsToRoles() {
    for (let role of this.roles) {
      for (let org of this.organizations) {
        if (org.id === role.organization_id) {
          role.organization = org;
          break;
        }
      }
    }
  }

  getRoleOrgName(role: RoleWithOrg): string {
    return role.organization ? role.organization.name : 'Any';
  }

  deleteRole(role: Role) {
    this.roles = removeMatchedIdFromArray(this.roles, role.id);
  }
}
