import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';

import { User } from 'src/app/interfaces/user';

import { deepcopy } from 'src/app/utils';
import { UserService } from 'src/app/services/api/user.service';
import { UserPermissionService } from 'src/app/services/user-permission.service';

@Component({
  selector: 'app-user-view',
  templateUrl: './user-view.component.html',
  styleUrls: ['./user-view.component.scss'],
})
export class UserViewComponent implements OnInit {
  @Input() user: User = {
    id: -1,
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    organization_id: -1,
    roles: [],
    rules: [],
  };
  @Output() deletingUser = new EventEmitter<User>();
  @Output() editingUser = new EventEmitter<User>();

  constructor(
    public userPermission: UserPermissionService,
    public userService: UserService
  ) {}

  ngOnInit(): void {
    this.user.is_being_edited = false;
  }

  deleteUser(user: User): void {
    this.userService.delete(user).subscribe(
      (data) => {
        this.deletingUser.emit(user);
      },
      (error) => {
        alert(error.error.msg);
      }
    );
  }

  editUser(user: User): void {
    user.is_being_edited = true;
    this.editingUser.emit(user);
  }
}
