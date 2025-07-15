import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { BaseCreateComponent } from 'src/app/components/admin-base/base-create/base-create.component';
import { ResourceForm } from 'src/app/models/api/resource.model';
import { BaseUser, UserCreate, UserForm } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { UserService } from 'src/app/services/user.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf } from '@angular/common';
import { MatCard, MatCardContent } from '@angular/material/card';
import { UserFormComponent } from '../../../../components/forms/user-form/user-form.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { ServerConfigService } from 'src/app/services/server-config.service';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { FileService } from 'src/app/services/file.service';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-user-create',
  templateUrl: './user-create.component.html',
  imports: [PageHeaderComponent, NgIf, MatCard, MatCardContent, UserFormComponent, MatProgressSpinner, TranslateModule]
})
export class UserCreateComponent extends BaseCreateComponent {
  isCreateServiceAccount: boolean = false;

  constructor(
    private router: Router,
    private userService: UserService,
    private serverConfigService: ServerConfigService,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private fileService: FileService
  ) {
    super();
    // if the route includes 'service-account', set isServiceAccount to true
    this.isCreateServiceAccount = this.router.url.includes('service-account');
  }

  async handleSubmit(userForm: ResourceForm): Promise<void> {
    this.isSubmitting = true;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const userCreate: UserCreate = (({ passwordRepeat, ...data }) => data)(userForm as UserForm);
    // don't send password if user doesn't have to be created in keycloak
    if (this.isCreateServiceAccount) {
      userCreate.is_service_account = true;
      delete userCreate.password;
    } else if (!(await this.serverConfigService.doesKeycloakManageUsersAndNodes())) {
      delete userCreate.password;
    }
    const user = await this.userService.createUser(userCreate);
    if (user.id) {
      // if the user is a service account, we want to open a dialog to download the
      // secret
      if (this.isCreateServiceAccount) {
        this.downloadServiceAccountSecret(user);
        this.alertServiceAccountDownload();
      } else {
        this.router.navigate([routePaths.users]);
      }
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel(): void {
    this.router.navigate([routePaths.users]);
  }

  downloadServiceAccountSecret(user: BaseUser): void {
    const filename = `service-account-secret-${user.username}.txt`;
    const text = `This file contains instructions on how to use the service account.

User details:
-------------

username: ${user.username}
secret: ${user.client_secret}

To login to the service account with the Python client, you need to run:

--------------------------------

from vantage6.client import Client

client = Client(
    server_url="${environment.server_url}${environment.api_path}",
    auth_url="${environment.auth_url}",
    auth_realm="${environment.keycloak_realm}",
)
client.initialize_service_account(
    client_secret="${user.client_secret}",
    username="${user.username}"
)
client.authenticate_service_account()

--------------------------------

Good luck!
    `;
    this.fileService.downloadTxtFile(text, filename);
  }

  alertServiceAccountDownload(): void {
    // open a dialog to download the secret
    const dialogRef = this.dialog.open(MessageDialogComponent, {
      data: {
        title: this.translateService.instant('user-create.service-account-download-dialog.title'),
        content: [
          this.translateService.instant('user-create.service-account-download-dialog.message'),
          this.translateService.instant('user-create.service-account-download-dialog.security-message')
        ],
        confirmButtonText: this.translateService.instant('general.close'),
        confirmButtonType: 'default'
      }
    });
    // after closing the dialog, navigate to the users page
    dialogRef.afterClosed().subscribe(() => {
      this.router.navigate([routePaths.users]);
    });
  }
}
