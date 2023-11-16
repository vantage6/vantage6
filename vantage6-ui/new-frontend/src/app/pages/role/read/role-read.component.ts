import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { Role, RoleLazyProperties } from 'src/app/models/api/role.model';
import { OperationType, ResourceType, Rule, ScopeType } from 'src/app/models/api/rule.model';
import { RoleService } from 'src/app/services/role.service';
import { RuleService } from 'src/app/services/rule.service';

@Component({
  selector: 'app-role-read',
  templateUrl: './role-read.component.html',
  styleUrls: ['./role-read.component.scss']
})
export class RoleReadComponent implements OnInit {
  @HostBinding('class') class = 'card-container';

  @Input() id = '';

  constructor(
    private roleService: RoleService,
    private ruleService: RuleService
  ) {}

  isLoading = true;
  role?: Role;

  allRules: Rule[] = [];
  testFixedRules: Rule[] = [
    { name: ResourceType.ORGANIZATION, operation: OperationType.CREATE, scope: ScopeType.GLOBAL, type: '', id: 999 }
  ];

  async ngOnInit(): Promise<void> {
    await this.initData();
  }

  private async initData(): Promise<void> {
    this.allRules = await this.ruleService.getAllRules();
    this.role = await this.roleService.getRole(this.id, [RoleLazyProperties.Rules, RoleLazyProperties.Users]);
    this.isLoading = false;
  }
}
