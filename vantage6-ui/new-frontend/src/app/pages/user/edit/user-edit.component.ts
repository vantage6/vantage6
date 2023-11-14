import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { User, UserEdit, UserForm, UserLazyProperties } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { UserService } from 'src/app/services/user.service';

@Component({
  selector: 'app-user-edit',
  templateUrl: './user-edit.component.html'
})
export class UserEditComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  @Input() id: string = '';

  isLoading: boolean = true;
  isSubmitting: boolean = false;
  user?: User;

  constructor(
    private router: Router,
    private userService: UserService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.isLoading = false;
  }

  async handleSubmit(userForm: UserForm) {
    if (!this.user) return;

    this.isSubmitting = true;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const userEdit: UserEdit = (({ password, passwordRepeat, organization_id, ...data }) => data)(userForm);
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

  private async initData(): Promise<void> {
    this.user = await this.userService.getUser(this.id, [UserLazyProperties.Organization, UserLazyProperties.Roles]);
  }
}
