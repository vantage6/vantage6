import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { Role } from 'src/app/interfaces/role';

import { getEmptyUser, User } from 'src/app/interfaces/user';

@Injectable({
  providedIn: 'root',
})
export class UserEditService {
  user = getEmptyUser();
  user_bhs = new BehaviorSubject<User>(this.user);
  available_roles: Role[] = [];
  available_roles_bhs = new BehaviorSubject<Role[]>(this.available_roles);

  constructor() {}

  set(user: User, roles: Role[]) {
    this.user = user;
    this.user_bhs.next(user);
    this.available_roles = roles;
    this.available_roles_bhs.next(roles);
  }

  setUser(user: User) {
    this.user_bhs.next(user);
  }

  setAvailableRoles(roles: Role[]) {
    this.available_roles_bhs.next(roles);
  }

  getUser() {
    return this.user;
  }

  getAvailableRoles() {
    return this.available_roles;
  }
}
