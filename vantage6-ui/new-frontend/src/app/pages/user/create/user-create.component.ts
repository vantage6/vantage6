import { Component, HostBinding } from '@angular/core';
import { Router } from '@angular/router';
import { UserCreate, UserForm } from 'src/app/models/api/user.model';
import { routePaths } from 'src/app/routes';
import { UserService } from 'src/app/services/user.service';

@Component({
  selector: 'app-user-create',
  templateUrl: './user-create.component.html',
  styleUrls: ['./user-create.component.scss']
})
export class UserCreateComponent {
  @HostBinding('class') class = 'card-container';
  routes = routePaths;

  isSubmitting: boolean = false;

  constructor(
    private router: Router,
    private userService: UserService
  ) {}

  async handleSubmit(userForm: UserForm): Promise<void> {
    this.isSubmitting = true;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const userCreate: UserCreate = (({ passwordRepeat, ...data }) => data)(userForm);
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
