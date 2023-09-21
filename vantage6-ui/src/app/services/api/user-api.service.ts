import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { User } from 'src/app/interfaces/user';

import { getIdsFromArray } from 'src/app/shared/utils';
import { BaseApiService } from 'src/app/services/api/base-api.service';
import { ResType } from 'src/app/shared/enum';
import { ModalService } from 'src/app/services/common/modal.service';
import { environment } from 'src/environments/environment';
import { Observable } from 'rxjs';

/**
 * Service for interacting with the user endpoints of the API
 */
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

  /**
   * Get data of a user to update or create a user on the API.
   *
   * @param user The user to get the data from.
   * @param exclude_own_permissions If a user is logged in, they are not allowed
   * to change their own permissions. This parameter indicates whether to
   * exclude the permissions of the user that is logged in.
   * @param include_password Whether to include the password of the user.
   * @returns The data of the user.
   */
  get_data(
    user: User,
    exclude_own_permissions: boolean = false,
    include_password = true
  ): any {
    let data: any = {
      username: user.username,
      email: user.email,
      firstname: user.first_name,
      lastname: user.last_name,
      organization_id: user.organization_id,
    };
    // do not include the roles/rules of a user that is logged in: they are
    // not allowed to change their own permissions, and this will lead to error
    if (!(user.is_logged_in && exclude_own_permissions)) {
      data.roles = getIdsFromArray(user.roles);
      data.rules = getIdsFromArray(user.rules);
    }
    if (user.password && include_password) {
      data.password = user.password;
    }
    return data;
  }

  update(user: User): Observable<any> {
    /**
     * Update a user in the API.
     *
     * @param user The user to update.
     * @returns An observable for the request response.
     */
    const data = this.get_data(user, true, false);
    return this.http.patch<any>(environment.api_url + '/user/' + user.id, data);
  }

  /**
   * Change a user's password via the API
   *
   * @param current_password The user's current password.
   * @param new_password The user's new password.
   * @returns An observable for the request response.
   */
  change_password(
    current_password: string, new_password: string
  ): Observable<any> {
    return this.http.patch<any>(environment.api_url + '/password/change', {
      current_password: current_password,
      new_password: new_password,
    });
  }
}
