import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { takeUntil, Subject } from 'rxjs';
import { BaseEditComponent } from 'src/app/components/admin-base/base-edit/base-edit.component';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { ResourceForm } from 'src/app/models/api/resource.model';
import { StoreUser, StoreUserForm, StoreUserFormSubmit, StoreUserLazyProperties } from 'src/app/models/api/store-user.model';
import { routePaths } from 'src/app/routes';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { StoreUserService } from 'src/app/services/store-user.service';
import { NgIf } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { StoreUserFormComponent } from '../../../../components/forms/store-user-form/store-user-form.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-store-user-edit',
  templateUrl: './store-user-edit.component.html',
  styleUrl: './store-user-edit.component.scss',
  standalone: true,
  imports: [NgIf, PageHeaderComponent, MatCard, MatCardContent, StoreUserFormComponent, MatProgressSpinner]
})
export class StoreUserEditComponent extends BaseEditComponent implements OnInit {
  user?: StoreUser;
  destroy$ = new Subject();
  store: AlgorithmStore | null = null;

  constructor(
    private router: Router,
    private storeUserService: StoreUserService,
    private chosenStoreService: ChosenStoreService
  ) {
    super();
  }

  override async ngOnInit(): Promise<void> {
    this.chosenStoreService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isInitialized) => {
        if (isInitialized) {
          this.store = this.chosenStoreService.store$.value;
          this.initData();
        }
      });
  }

  protected async initData(): Promise<void> {
    if (!this.store) return;
    this.user = await this.storeUserService.getUser(this.store.url, this.id, [StoreUserLazyProperties.Roles]);
    this.isLoading = false;
  }

  protected async handleSubmit(userForm: ResourceForm): Promise<void> {
    if (!this.user || !this.store) return;

    const userFormSubmit: StoreUserFormSubmit = {
      roles: (userForm as StoreUserForm).roles.map((role) => role.id)
    };

    this.isSubmitting = true;
    const user = await this.storeUserService.editUser(this.store.url, this.user.id, userFormSubmit);
    if (user.id) {
      this.router.navigate([routePaths.storeUser, user.id]);
    } else {
      this.isSubmitting = false;
    }
  }

  protected handleCancel(): void {
    this.router.navigate([routePaths.storeUser, this.id]);
  }

  getTitle(): string {
    return this.user ? `${this.user.username} @ ${this.user.server.url}` : '';
  }
}
