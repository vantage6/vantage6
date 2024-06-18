import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { BaseCreateComponent } from 'src/app/components/admin-base/base-create/base-create.component';
import { ResourceForm } from 'src/app/models/api/resource.model';
import { UserCreate, UserForm } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { UserService } from 'src/app/services/user.service';

@Component({
  selector: 'app-user-create',
  templateUrl: './user-create.component.html'
})
export class UserCreateComponent extends BaseCreateComponent {
  constructor(
    private router: Router,
    private userService: UserService
  ) {
    super();
  }

  async handleSubmit(userForm: ResourceForm): Promise<void> {
    this.isSubmitting = true;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const userCreate: UserCreate = (({ passwordRepeat, ...data }) => data)(userForm as UserForm);
    const user = await this.userService.createUser(userCreate);
    if (user.id) {
      this.router.navigate([routePaths.users]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel(): void {
    this.router.navigate([routePaths.users]);
  }
}
