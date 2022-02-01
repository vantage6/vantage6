import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { Role } from '../interfaces/role';

import { getEmptyUser, User } from '../interfaces/user';

@Injectable({
  providedIn: 'root',
})
export class UserEditService {
  user = new BehaviorSubject<User>(getEmptyUser());
  available_roles = new BehaviorSubject<Role[]>([]);

  constructor() {}

  set(user: User, roles: Role[]) {
    this.user.next(user);
    this.available_roles.next(roles);
  }

  setUser(user: User) {
    this.user.next(user);
  }

  setAvailableRoles(roles: Role[]) {
    this.available_roles.next(roles);
  }

  getUser() {
    return this.user.asObservable();
  }

  getAvailableRoles() {
    return this.available_roles.asObservable();
  }
}
