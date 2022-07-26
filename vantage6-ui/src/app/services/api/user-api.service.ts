import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Rule } from 'src/app/interfaces/rule';
import { User } from 'src/app/interfaces/user';

import { getIdsFromArray } from 'src/app/shared/utils';
import { BaseApiService } from 'src/app/services/api/base-api.service';
import { ResType } from 'src/app/shared/enum';
import { ModalService } from 'src/app/services/common/modal.service';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root',
})
export class UserApiService extends BaseApiService {
  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.USER, http, modalService);
  }

  get_data(user: User): any {
    let data: any = {
      username: user.username,
      email: user.email,
      firstname: user.first_name,
      lastname: user.last_name,
      organization_id: user.organization_id,
      roles: getIdsFromArray(user.roles),
      rules: getIdsFromArray(user.rules),
    };
    if (user.password) {
      data.password = user.password;
    }
    return data;
  }

  change_password(current_password: string, new_password: string) {
    return this.http.post<any>(environment.api_url + '/recover/change', {
      current_password: current_password,
      new_password: new_password,
    });
  }
}
