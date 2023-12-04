import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Organization } from 'src/app/models/api/organization.model';
import { RoleForm } from 'src/app/models/api/role.model';
import { OperationType, ResourceType, Rule } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { OrganizationService } from 'src/app/services/organization.service';
import { PermissionService } from 'src/app/services/permission.service';
import { RoleService } from 'src/app/services/role.service';
import { RuleService } from 'src/app/services/rule.service';

@Component({
  selector: 'app-role-create',
  templateUrl: './role-create.component.html',
  styleUrls: ['./role-create.component.scss']
})
export class RoleCreateComponent implements OnInit {
  isSubmitting = false;
  selectableRules: Rule[] = [];
  selectableOrganizations: Organization[] = [];

  constructor(
    private router: Router,
    private ruleService: RuleService,
    private roleService: RoleService,
    private organizationService: OrganizationService,
    private permissionService: PermissionService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
  }

  async handleSubmit(roleForm: RoleForm): Promise<void> {
    this.isSubmitting = true;

    try {
      await this.roleService.createRole(roleForm);
    } catch (error) {
      /* Error handling */
    } finally {
      this.router.navigate([routePaths.roles]);
    }

    this.isSubmitting = false;
  }

  handleCancel(): void {
    console.log('test');
  }

  /* TODO: bundle promises */
  private async initData(): Promise<void> {
    this.selectableRules = await this.ruleService.getAllRules();
    this.selectableOrganizations = await this.organizationService.getAllowedOrganizations(ResourceType.ROLE, OperationType.CREATE);
  }
}
