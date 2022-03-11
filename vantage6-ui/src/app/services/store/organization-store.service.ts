import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

import {
  EMPTY_ORGANIZATION,
  Organization,
} from 'src/app/interfaces/organization';
import { StoreBaseService } from './store-base.service';

@Injectable({
  providedIn: 'root',
})
export class OrganizationStoreService extends StoreBaseService {
  org = new BehaviorSubject<Organization>(EMPTY_ORGANIZATION);
  org_list = new BehaviorSubject<Organization[]>([]);

  constructor() {
    super();
  }

  setSingle(org: Organization) {
    this.org.next(org);
  }

  getSingle() {
    return this.org.asObservable();
  }

  setList(orgs: Organization[]) {
    this.org_list.next(orgs);
  }

  getList() {
    return this.org_list.asObservable();
  }

  add(org: Organization) {
    const updated_list = [...this.org_list.value, org];
    this.org_list.next(updated_list);
  }

  remove(org: Organization) {
    alert('Organizations cannot be removed?!');
  }

  hasListStored(): boolean {
    return this.org_list.value.length > 0;
  }
}
