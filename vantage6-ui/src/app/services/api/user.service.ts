import { Injectable } from '@angular/core';

import { User } from 'src/app/interfaces/user';

@Injectable({
  providedIn: 'root',
})
export class UserService {
  constructor() {}

  list() {}

  get(id: number) {}

  update(id: number, user: User) {}

  create(id: number, user: User) {}

  delete(id: number) {}
}
