import { Component, OnDestroy, OnInit } from '@angular/core';
import { MatSlideToggleChange } from '@angular/material/slide-toggle';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { takeUntil } from 'rxjs';
import { BaseReadComponent } from 'src/app/components/admin-base/base-read/base-read.component';
import { OperationType, ResourceType, Rule, ScopeType } from 'src/app/models/api/rule.model';
import { User, UserLazyProperties } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { HandleConfirmDialogService } from 'src/app/services/handle-confirm-dialog.service';
import { PermissionService } from 'src/app/services/permission.service';
import { RuleService } from 'src/app/services/rule.service';
import { UserService } from 'src/app/services/user.service';
import { NgIf, NgFor } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatIconButton } from '@angular/material/button';
import { MatMenuTrigger, MatMenu, MatMenuItem } from '@angular/material/menu';
import { MatIcon } from '@angular/material/icon';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { ChipComponent } from '../../../../components/helpers/chip/chip.component';
import { PermissionsMatrixServerComponent } from '../../../../components/permissions-matrix/server/permissions-matrix-server.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-user-read',
  styleUrls: ['./user-read.component.scss'],
  templateUrl: './user-read.component.html',
  standalone: true,
  imports: [
    NgIf,
    PageHeaderComponent,
    MatIconButton,
    MatMenuTrigger,
    MatIcon,
    MatMenu,
    MatMenuItem,
    RouterLink,
    MatCard,
    MatCardHeader,
    MatCardTitle,
    MatCardContent,
    ChipComponent,
    NgFor,
    PermissionsMatrixServerComponent,
    MatProgressSpinner,
    TranslateModule
  ]
})
export class UserReadComponent extends BaseReadComponent implements OnInit, OnDestroy {
  showUserSpecificRulesOnly: boolean = false;
  user: User | null = null;

  allUserRules: Rule[] = [];
  rolesRules: Rule[] = [];
  userSpecificRules: Rule[] = [];
  rulesForDisplay: Rule[] = [];

  constructor(
    protected override handleConfirmDialogService: HandleConfirmDialogService,
    private router: Router,
    private userService: UserService,
    protected override translateService: TranslateService,
    private permissionService: PermissionService,
    private ruleService: RuleService
  ) {
    super(handleConfirmDialogService, translateService);
  }

  override async ngOnInit(): Promise<void> {
    super.ngOnInit();
    this.processRulesForDisplay();
  }

  protected async initData(): Promise<void> {
    this.user = await this.userService.getUser(this.id, [UserLazyProperties.Organization, UserLazyProperties.Roles]);
    this.setPermissions();

    this.allUserRules = await this.ruleService.getRules({ user_id: this.user.id });
    this.rolesRules = await this.ruleService.getRulesOfRoles(this.user.roles.map((role) => role.id));
    this.userSpecificRules = this.determineUserRules(this.rolesRules, this.allUserRules);
    this.isLoading = false;
  }

  processRulesForDisplay(): void {
    const rules = this.userSpecificRules;
    this.rulesForDisplay = this.showUserSpecificRulesOnly ? rules : rules.concat(this.rolesRules);
  }

  /* Determine the set of selected rules that has no overlap with role rules. */
  private determineUserRules(roleRules: Rule[], userSelectedRules: Rule[]): Rule[] {
    if (!roleRules || !userSelectedRules) return [];
    return userSelectedRules.filter((userRule) => !roleRules.some((roleRule) => roleRule.id === userRule.id));
  }

  handleShowUserSpecificRulesChange(event: MatSlideToggleChange): void {
    this.showUserSpecificRulesOnly = event.checked;
    this.processRulesForDisplay();
  }

  async handleDelete(): Promise<void> {
    this.handleDeleteBase(
      this.user,
      this.translateService.instant('user-read.delete-dialog.title', { name: this.user?.username }),
      this.translateService.instant('user-read.delete-dialog.content'),
      this.executeDeleteUser.bind(this)
    );
  }

  protected async executeDeleteUser(): Promise<void> {
    if (!this.user) return;
    this.isLoading = true;
    await this.userService.deleteUser(this.user.id);
    this.router.navigate([routePaths.users]);
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canDelete =
            !!this.user?.organization &&
            this.permissionService.isAllowedForOrg(ResourceType.USER, OperationType.DELETE, this.user.organization.id);
          this.canEdit =
            (!!this.user?.organization &&
              this.permissionService.isAllowedForOrg(ResourceType.USER, OperationType.EDIT, this.user.organization.id)) ||
            (this.user?.id === this.permissionService.activeUser?.id &&
              this.permissionService.isAllowed(ScopeType.OWN, ResourceType.USER, OperationType.EDIT));
        }
      });
  }
}
