import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { User } from 'src/app/interfaces/user';
import { Resource } from 'src/app/shared/types';
import { ApiUserService } from '../api/api-user.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';

@Injectable({
  providedIn: 'root',
})
export class UserDataService extends BaseDataService {
  constructor(
    protected apiService: ApiUserService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async get(
    id: number,
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Observable<User>> {
    return (await super.get(
      id,
      convertJsonFunc,
      additionalConvertArgs,
      force_refresh
    )) as Observable<User>;
  }

  async list(
    convertJsonFunc: Function,
    additionalConvertArgs: Resource[][] = [],
    force_refresh: boolean = false
  ): Promise<Observable<User[]>> {
    return (await super.list(
      convertJsonFunc,
      additionalConvertArgs,
      force_refresh
    )) as Observable<User[]>;
  }
}
