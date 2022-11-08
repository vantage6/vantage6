import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { User } from 'src/app/interfaces/user';
import { UserApiService } from '../api/user-api.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';

@Injectable({
  providedIn: 'root',
})
export class UserDataService extends BaseDataService {
  constructor(
    protected apiService: UserApiService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async get(
    id: number,
    roles: Role[],
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<User> {
    return (await super.get_base(
      id,
      this.convertJsonService.getUser,
      [roles, rules],
      force_refresh
    )) as User;
  }

  async list(
    roles: Role[],
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<Observable<User[]>> {
    return (await super.list_base(
      this.convertJsonService.getUser,
      [roles, rules],
      force_refresh
    )) as Observable<User[]>;
  }

  async list_with_params(
    roles: Role[] = [],
    rules: Rule[] = [],
    request_params: any = {},
    save: boolean = true
  ): Promise<User[]> {
    return (await super.list_with_params_base(
      this.convertJsonService.getUser,
      [roles, rules],
      request_params,
      save
    )) as User[];
  }

  async org_list(
    organization_id: number,
    roles: Role[],
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<User[]> {
    return (await super.org_list_base(
      organization_id,
      this.convertJsonService.getUser,
      [roles, rules],
      force_refresh
    )) as User[];
  }
}
