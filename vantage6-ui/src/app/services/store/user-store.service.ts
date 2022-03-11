import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

import { getEmptyUser, User } from 'src/app/interfaces/user';
import { removeMatchedIdFromArray } from 'src/app/shared/utils';
import { StoreBaseService } from './store-base.service';

@Injectable({
  providedIn: 'root',
})
export class UserStoreService extends StoreBaseService {
  user = new BehaviorSubject<User>(getEmptyUser());
  users = new BehaviorSubject<User[]>([]);

  constructor() {
    super();
  }

  setSingle(user: User) {
    this.user.next(user);
  }

  getSingle() {
    return this.user.asObservable();
  }

  setList(users: User[]) {
    this.users.next(users);
  }

  getList() {
    return this.users.asObservable();
  }

  add(user: User) {
    const updated_list = [...this.users.value, user];
    this.users.next(updated_list);
  }

  remove(user: User) {
    this.users.next(removeMatchedIdFromArray(this.users.value, user.id));
  }

  hasListStored(): boolean {
    return this.users.value.length > 0;
  }
}
