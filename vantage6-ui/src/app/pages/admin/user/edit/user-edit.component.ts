import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { BaseEditComponent } from 'src/app/components/admin-base/base-edit/base-edit.component';
import { ResourceForm } from 'src/app/models/api/resource.model';
import { User, UserEdit, UserForm, UserLazyProperties } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { UserService } from 'src/app/services/user.service';

@Component({
  selector: 'app-user-edit',
  templateUrl: './user-edit.component.html'
})
export class UserEditComponent extends BaseEditComponent implements OnInit {
  user?: User;

  constructor(
    private router: Router,
    private userService: UserService
  ) {
    super();
  }

  protected async handleSubmit(userForm: ResourceForm): Promise<void> {
    const form = userForm as UserForm;
    if (!this.user) return;

    this.isSubmitting = true;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const userEdit: UserEdit = (({ password, passwordRepeat, organization_id, ...data }) => data)(form);
    const user = await this.userService.editUser(this.user?.id.toString(), userEdit);
    if (user.id) {
      this.router.navigate([routePaths.user, user.id]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel() {
    this.router.navigate([routePaths.user, this.id]);
  }

  protected async initData(): Promise<void> {
    this.user = await this.userService.getUser(this.id, [
      UserLazyProperties.Organization,
      UserLazyProperties.Roles,
      UserLazyProperties.Rules
    ]);
    this.isLoading = false;
  }
}
