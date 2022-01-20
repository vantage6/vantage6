import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { EMPTY_ROLE, Role } from '../interfaces/role';

@Injectable({
  providedIn: 'root',
})
export class RoleEditService {
  role = new BehaviorSubject<Role>(EMPTY_ROLE);

  constructor() {}

  setRole(role: Role) {
    this.role.next(role);
  }

  getRole() {
    return this.role.asObservable();
  }
}
