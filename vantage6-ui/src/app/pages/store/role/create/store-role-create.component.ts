import { Component, HostBinding, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { BaseCreateComponent } from 'src/app/components/admin-base/base-create/base-create.component';
import { StoreRoleForm } from 'src/app/models/api/store-role.model';
import { StoreRule } from 'src/app/models/api/rule.model';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StoreRoleService } from 'src/app/services/store-role.service';
import { StoreRuleService } from 'src/app/services/store-rule.service';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { routePaths } from 'src/app/routes';
import { ResourceForm } from 'src/app/models/api/resource.model';

@Component({
  selector: 'app-store-role-create',
  templateUrl: './store-role-create.component.html',
  styleUrls: ['./store-role-create.component.scss']
})
export class StoreRoleCreateComponent extends BaseCreateComponent implements OnInit {

    selectableRules: StoreRule[] = [];
    store: AlgorithmStore | null = null;
    destroy$ = new Subject();
    
    
    constructor(
      private router: Router,
      private ruleService: StoreRuleService,
      private roleService: StoreRoleService,
      private chosenStoreService: ChosenStoreService) {
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
  
    async handleSubmit(roleForm: ResourceForm): Promise<void> {
      this.isSubmitting = true;
      if (!this.store) return;
      try {
        await this.roleService.createRole(this.store.url, roleForm as StoreRoleForm);
      } catch (error) {
        /* TODO Error handling */
      } finally {
        this.router.navigate([routePaths.storeRoles]);
      }
  
      this.isSubmitting = false;
    }
  
    handleCancel(): void {
      this.router.navigate([routePaths.roles]);
    }
  
    /* TODO: bundle promises */
    private async initData(): Promise<void> {
      this.store = this.chosenStoreService.store$.value;
      if (!this.store) return;
      this.selectableRules = await this.ruleService.getRules(this.store.url);
    }
  }
