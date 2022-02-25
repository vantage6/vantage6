import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

import {
  EMPTY_ORGANIZATION,
  Organization,
} from 'src/app/interfaces/organization';

@Injectable({
  providedIn: 'root',
})
export class OrganizationStoreService {
  org = new BehaviorSubject<Organization>(EMPTY_ORGANIZATION);

  constructor() {}

  setOrganization(org: Organization) {
    this.org.next(org);
  }

  getOrganization() {
    return this.org.asObservable();
  }
}
