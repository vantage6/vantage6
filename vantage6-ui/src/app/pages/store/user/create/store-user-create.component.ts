import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { BaseCreateComponent } from 'src/app/components/admin-base/base-create/base-create.component';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { ResourceForm } from 'src/app/models/api/resource.model';
import { StoreUserCreate, StoreUserForm } from 'src/app/models/api/store-user.model';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StoreUserService } from 'src/app/services/store-user.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf } from '@angular/common';
import { MatCard, MatCardContent } from '@angular/material/card';
import { StoreUserFormComponent } from '../../../../components/forms/store-user-form/store-user-form.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-store-user-create',
  templateUrl: './store-user-create.component.html',
  styleUrl: './store-user-create.component.scss',
  standalone: true,
  imports: [PageHeaderComponent, NgIf, MatCard, MatCardContent, StoreUserFormComponent, MatProgressSpinner, TranslateModule]
})
export class StoreUserCreateComponent extends BaseCreateComponent implements OnInit {
  destroy$ = new Subject();
  store: AlgorithmStore | null = null;

  constructor(
    private router: Router,
    private storeUserService: StoreUserService,
    private chosenStoreService: ChosenStoreService
  ) {
    super();
  }

  async ngOnInit(): Promise<void> {
    this.chosenStoreService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isInitialized) => {
        if (isInitialized) {
          this.store = this.chosenStoreService.store$.value;
        }
      });
  }

  async handleSubmit(userForm: ResourceForm): Promise<void> {
    if (!this.store) return;
    this.isSubmitting = true;
    const storeUserCreate: StoreUserCreate = {
      username: (userForm as StoreUserForm).username,
      roles: (userForm as StoreUserForm).roles.map((role) => role.id)
    };
    const storeUser = await this.storeUserService.createUser(this.store.url, storeUserCreate);
    if (storeUser.id) {
      this.router.navigate([this.routes.storeUsers]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel(): void {
    this.router.navigate([this.routes.storeUsers]);
  }
}
