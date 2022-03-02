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
  org_list = new BehaviorSubject<Organization[]>([]);

  constructor() {}

  setOrganization(org: Organization) {
    this.org.next(org);
  }

  getOrganization() {
    return this.org.asObservable();
  }

  setOrganizationList(orgs: Organization[]) {
    this.org_list.next(orgs);
  }

  getOrganizationList() {
    return this.org_list.asObservable();
  }

  addOrganization(org: Organization) {
    const updated_list = [...this.org_list.value, org];
    this.org_list.next(updated_list);
  }
}
