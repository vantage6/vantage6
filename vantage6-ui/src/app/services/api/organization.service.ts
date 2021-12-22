import { Injectable } from '@angular/core';

import { Organization } from 'src/app/interfaces/organization';

@Injectable({
  providedIn: 'root',
})
export class OrganizationService {
  constructor() {}

  list() {}

  get(id: number) {}

  update(id: number, organization: Organization) {}

  create(id: number, organization: Organization) {}

  delete(id: number) {}
}
