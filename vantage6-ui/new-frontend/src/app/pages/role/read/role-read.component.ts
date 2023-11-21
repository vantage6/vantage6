import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Role, RoleLazyProperties } from 'src/app/models/api/role.model';
import { Rule } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
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
    private ruleService: RuleService,
    private translateService: TranslateService
  ) {}

  isLoading = true;
  role?: Role;
  roleRules: Rule[] = [];
  allRules: Rule[] = [];
  userTable?: TableData;
  isEditing: boolean = false;

  /* Bound variables to permission matrix. */
  preselectedRules: Rule[] = [];
  selectableRules: Rule[] = [];
  fixedSelectedRules: Rule[] = [];

  changedRules?: Rule[];

  async ngOnInit(): Promise<void> {
    await this.initData();
  }

  private async initData(): Promise<void> {
    this.allRules = await this.ruleService.getAllRules();
    this.role = await this.roleService.getRole(this.id, [RoleLazyProperties.Users]);
    this.userTable = {
      columns: [
        { id: 'username', label: this.translateService.instant('user.username') },
        { id: 'firstname', label: this.translateService.instant('user.first-name') },
        { id: 'lastname', label: this.translateService.instant('user.last-name') },
        { id: 'email', label: this.translateService.instant('user.email') }
      ],
      rows: this.role.users.map((user) => ({
        id: user.id.toString(),
        columnData: { ...user }
      }))
    };
    this.roleRules = await this.ruleService.getAllRules(this.id);
    this.enterEditMode(false);
    this.isLoading = false;
  }

  private enterEditMode(edit: boolean): void {
    this.isEditing = edit;
    if (edit) {
      this.preselectedRules = this.roleRules;
      this.fixedSelectedRules = [];
      this.selectableRules = this.allRules;
    } else {
      this.preselectedRules = [];
      this.fixedSelectedRules = this.roleRules;
      this.selectableRules = this.roleRules;
    }
  }

  public handleEnterEditMode(): void {
    this.enterEditMode(true);
  }

  public handleCancelEdit(): void {
    this.enterEditMode(false);
  }

  public get showUserTable(): boolean {
    return this.userTable != undefined && this.userTable.rows.length > 0;
  }

  public handleChangedSelection(rules: Rule[]): void {
    this.changedRules = rules;
  }

  public async handleSubmitEdit(): Promise<void> {
    if (!this.role || !this.changedRules) return;
    this.isLoading = true;
    const role: Role = { ...this.role, rules: this.changedRules };
    await this.roleService.patchRole(role);
    this.changedRules = [];
    this.initData();
  }
}
