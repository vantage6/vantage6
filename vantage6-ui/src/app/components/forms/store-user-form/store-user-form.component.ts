import { Component, Input, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
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

@Component({
  selector: 'app-store-user-form',
  templateUrl: './store-user-form.component.html',
  styleUrl: './store-user-form.component.scss'
})
export class StoreUserFormComponent extends BaseFormComponent implements OnInit {
  @Input() user?: StoreUser;
  userRoles: StoreRole[] = [];
  userRules: StoreRule[] = [];
  availableRoles: StoreRole[] = [];
  store: AlgorithmStore | null = null;
  compareRolesForSelection = compareObjIDs;

  form = this.fb.nonNullable.group({
    roles: [[] as StoreRole[], [Validators.required]]
  });

  constructor(
    private fb: FormBuilder,
    private storeRoleService: StoreRoleService,
    private chosenStoreService: ChosenStoreService,
    private storeRuleService: StoreRuleService
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

    // if the user is being created, initialization is done
    if (!this.user) {
      this.isLoading = false;
      return;
    }

    // if the user is being edited, set the form values
    this.userRoles = this.user.roles;
    this.form.controls.roles.setValue(this.userRoles);
    this.isLoading = false;
  }
}
