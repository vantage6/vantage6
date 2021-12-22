import { Injectable } from '@angular/core';

import { Role } from 'src/app/interfaces/role';

@Injectable({
  providedIn: 'root',
})
export class RoleService {
  constructor() {}

  list() {}

  get(id: number) {}

  update(id: number, role: Role) {}

  create(id: number, role: Role) {}

  delete(id: number) {}
}
