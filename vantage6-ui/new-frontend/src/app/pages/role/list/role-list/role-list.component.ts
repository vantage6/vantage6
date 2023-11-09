import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { PermissionService } from 'src/app/services/permission.service';
import { RoleService } from 'src/app/services/role.service';

@Component({
  selector: 'app-role-list',
  templateUrl: './role-list.component.html',
  styleUrls: ['./role-list.component.scss']
})
export class RoleListComponent implements OnInit {
  isLoading: boolean = true;
  canCreate: boolean = false;
  table?: TableData;
  routes = routePaths;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private roleService: RoleService,
    private permissionService: PermissionService
  ) {}

  async ngOnInit(): Promise<void> {
    this.canCreate = this.permissionService.isAllowed(ScopeType.GLOBAL, ResourceType.ROLE, OperationType.CREATE);
    await this.initData();
  }

  private async initData() {
    await this.getRoles();
    this.isLoading = false;
  }

  private async getRoles() {
    const result = await this.roleService.getRoles();

    this.table = {
      columns: [{ id: 'name', label: this.translateService.instant('role.name') }],
      rows: result.map((_) => ({
        id: _.id.toString(),
        columnData: {
          name: _.name
        }
      }))
    };
  }

  handleTableClick(id: string): void {
    //   this.router.navigate([routePaths.collaboration, id]);
  }
}
