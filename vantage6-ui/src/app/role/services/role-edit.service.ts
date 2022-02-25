import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { getEmptyRole, Role } from 'src/app/interfaces/role';

@Injectable({
  providedIn: 'root',
})
export class RoleEditService {
  role = new BehaviorSubject<Role>(getEmptyRole());

  constructor() {}

  setRole(role: Role) {
    this.role.next(role);
  }

  getRole() {
    return this.role.asObservable();
  }
}
