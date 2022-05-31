import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Role } from 'src/app/interfaces/role';
import { ApiRoleService } from 'src/app/services/api/api-role.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { Resource } from 'src/app/shared/types';
import { BaseDataService } from 'src/app/services/data/base-data.service';

@Injectable({
  providedIn: 'root',
})
export class RoleDataService extends BaseDataService {
  assignable_roles: Role[] = [];

  constructor(
    protected apiService: ApiRoleService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async get(
    id: number,
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Observable<Role>> {
    return (await super.get(
      id,
      convertJsonFunc,
      additionalConvertArgs,
      force_refresh
    )) as Observable<Role>;
  }

  async list(
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Observable<Role[]>> {
    return (await super.list(
      convertJsonFunc,
      additionalConvertArgs,
      force_refresh
    )) as Observable<Role[]>;
  }

  // TODO why not determine which roles are assignable when needed? Shouldnt come
  // from a service as it is user-dependent
  listAssignable(): Role[] {
    return this.assignable_roles;
  }

  setListAssignable(roles: Role[]): void {
    this.assignable_roles = roles;
  }
}
