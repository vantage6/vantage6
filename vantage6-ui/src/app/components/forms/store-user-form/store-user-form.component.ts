import { Component, Input, OnInit } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { takeUntil } from 'rxjs';
import { StoreUser } from 'src/app/models/api/store-user.model';
import { StoreRoleService } from 'src/app/services/store-role.service';
import { BaseFormComponent } from '../../admin-base/base-form/base-form.component';
import { StoreRole } from 'src/app/models/api/store-role.model';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { compareObjIDs } from 'src/app/helpers/general.helper';
import { StoreRule } from 'src/app/models/api/rule.model';
import { StoreRuleService } from 'src/app/services/store-rule.service';
import { UserService } from 'src/app/services/user.service';
import { BaseUser } from 'src/app/models/api/user.model';
import { PermissionService } from 'src/app/services/permission.service';
import { NgIf, NgFor } from '@angular/common';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatSelect } from '@angular/material/select';
import { MatOption } from '@angular/material/core';
import { PermissionsMatrixStoreComponent } from '../../permissions-matrix/store/permissions-matrix-store.component';
import { MatButton } from '@angular/material/button';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-store-user-form',
  templateUrl: './store-user-form.component.html',
  styleUrl: './store-user-form.component.scss',
  standalone: true,
  imports: [
    NgIf,
    ReactiveFormsModule,
    MatFormField,
    MatLabel,
    MatSelect,
    NgFor,
    MatOption,
    PermissionsMatrixStoreComponent,
    MatButton,
    MatProgressSpinner,
    TranslateModule
  ]
})
export class StoreUserFormComponent extends BaseFormComponent implements OnInit {
  @Input() user?: StoreUser;
  userRoles: StoreRole[] = [];
  userRules: StoreRule[] = [];
  availableRoles: StoreRole[] = [];
  serverUsers: BaseUser[] = [];
  store: AlgorithmStore | null = null;
  compareRolesForSelection = compareObjIDs;

  form = this.fb.nonNullable.group({
    username: ['', [Validators.required]],
    roles: [[] as StoreRole[], [Validators.required]]
  });

  constructor(
    private fb: FormBuilder,
    private storeRoleService: StoreRoleService,
    private chosenStoreService: ChosenStoreService,
    private storeRuleService: StoreRuleService,
    private userService: UserService,
    private permissionService: PermissionService
  ) {
    super();
  }

  async ngOnInit(): Promise<void> {
    this.chosenStoreService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isInitialized) => {
        if (isInitialized) {
          this.initData();
        }
      });
  }

  private setupForm(): void {
    if (this.isEdit) {
      this.form.controls.username.disable();
    }
    this.form.controls.roles.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (roles) => {
      this.processRules(roles);
    });
  }

  private async processRules(roles: StoreRole[]): Promise<void> {
    if (!this.store) return;
    const roleIDs = roles.map((role) => role.id);
    this.userRules = await this.storeRuleService.getRulesForRoles(this.store?.url, roleIDs);
  }

  private async initData(): Promise<void> {
    this.isEdit = !!this.user;
    this.store = this.chosenStoreService.store$.value;
    if (!this.store) return;
    this.availableRoles = await this.storeRoleService.getRoles(this.store.url);
    this.setupForm();

    if (!this.user) {
      // if the user is being created, get the users from the server
      this.serverUsers = await this.userService.getUsers();
      // remove the current user from the list
      this.serverUsers = this.serverUsers.filter((serverUser) => serverUser.id !== this.permissionService.activeUser?.id);
    } else {
      // if the user is being edited, set the form values
      this.userRoles = this.user.roles;
      this.form.controls.roles.setValue(this.userRoles);
    }
    this.isLoading = false;
  }
}
