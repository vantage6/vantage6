import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSlideToggleChange } from '@angular/material/slide-toggle';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { OperationType, ResourceType, Rule } from 'src/app/models/api/rule.model';
import { User, UserLazyProperties } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { PermissionService } from 'src/app/services/permission.service';
import { RuleService } from 'src/app/services/rule.service';
import { UserService } from 'src/app/services/user.service';

@Component({
  selector: 'app-user-read',
  styleUrls: ['./user-read.component.scss'],
  templateUrl: './user-read.component.html'
})
export class UserReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';

  destroy$ = new Subject();
  routes = routePaths;

  isLoading: boolean = true;
  canDelete: boolean = false;
  canEdit: boolean = false;
  showUserSpecificRulesOnly: boolean = false;
  user: User | null = null;

  allUserRules: Rule[] = [];
  rolesRules: Rule[] = [];
  userSpecificRules: Rule[] = [];
  rulesForDisplay: Rule[] = [];

  constructor(
    private dialog: MatDialog,
    private router: Router,
    private userService: UserService,
    private translateService: TranslateService,
    private permissionService: PermissionService,
    private ruleService: RuleService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.processRulesForDisplay();
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  private async initData(): Promise<void> {
    this.user = await this.userService.getUser(this.id, [UserLazyProperties.Organization, UserLazyProperties.Roles]);
    this.canDelete =
      !!this.user.organization &&
      this.permissionService.isAllowedForOrg(ResourceType.USER, OperationType.DELETE, this.user.organization.id);
    this.canEdit =
      !!this.user.organization && this.permissionService.isAllowedForOrg(ResourceType.USER, OperationType.EDIT, this.user.organization.id);
    this.isLoading = false;

    this.allUserRules = await this.ruleService.getRules({ user_id: this.user.id, no_pagination: 1 });
    this.rolesRules = await this.ruleService.getRulesOfRoles(this.user.roles.map((role) => role.id));
    this.userSpecificRules = this.determineUserRules(this.rolesRules, this.allUserRules);
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
    if (!this.user) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('user-read.delete-dialog.title', { name: this.user.username }),
        content: this.translateService.instant('user-read.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === true) {
          if (!this.user) return;
          this.isLoading = true;
          await this.userService.deleteUser(this.user.id);
          this.router.navigate([routePaths.users]);
        }
      });
  }
}
