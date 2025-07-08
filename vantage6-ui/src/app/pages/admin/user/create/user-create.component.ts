import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { BaseCreateComponent } from 'src/app/components/admin-base/base-create/base-create.component';
import { ResourceForm } from 'src/app/models/api/resource.model';
import { UserCreate, UserForm } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { UserService } from 'src/app/services/user.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf } from '@angular/common';
import { MatCard, MatCardContent } from '@angular/material/card';
import { UserFormComponent } from '../../../../components/forms/user-form/user-form.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { ServerConfigService } from 'src/app/services/server-config.service';

@Component({
  selector: 'app-user-create',
  templateUrl: './user-create.component.html',
  imports: [PageHeaderComponent, NgIf, MatCard, MatCardContent, UserFormComponent, MatProgressSpinner, TranslateModule]
})
export class UserCreateComponent extends BaseCreateComponent {
  constructor(
    private router: Router,
    private userService: UserService,
    private serverConfigService: ServerConfigService
  ) {
    super();
  }

  async handleSubmit(userForm: ResourceForm): Promise<void> {
    this.isSubmitting = true;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const userCreate: UserCreate = (({ passwordRepeat, ...data }) => data)(userForm as UserForm);
    // don't send password if user doesn't have to be created in keycloak
    if (!(await this.serverConfigService.doesKeycloakManageUsersAndNodes())) {
      delete userCreate.password;
    }
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
