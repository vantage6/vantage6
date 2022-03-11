import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { getEmptyRole, Role } from 'src/app/interfaces/role';
import { removeMatchedIdFromArray } from 'src/app/shared/utils';
import { StoreBaseService } from './store-base.service';

@Injectable({
  providedIn: 'root',
})
export class RoleStoreService extends StoreBaseService {
  role = new BehaviorSubject<Role>(getEmptyRole());
  roles = new BehaviorSubject<Role[]>([]);
  assignable_roles = new BehaviorSubject<Role[]>([]);

  constructor() {
    super();
  }

  setSingle(role: Role) {
    this.role.next(role);
  }

  getSingle() {
    return this.role.asObservable();
  }

  setList(roles: Role[]) {
    this.roles.next(roles);
  }

  setListAssignable(roles: Role[]) {
    this.assignable_roles.next(roles);
  }

  getList() {
    return this.roles.asObservable();
  }

  getListAssignable() {
    return this.assignable_roles.asObservable();
  }

  add(role: Role) {
    const updated_list = [...this.roles.value, role];
    this.roles.next(updated_list);
  }

  remove(role: Role) {
    this.roles.next(removeMatchedIdFromArray(this.roles.value, role.id));
  }

  hasListStored(): boolean {
    return this.roles.value.length > 0;
  }
}
