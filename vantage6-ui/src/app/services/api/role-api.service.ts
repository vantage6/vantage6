import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';

import { getIdsFromArray } from 'src/app/shared/utils';
import { BaseApiService } from 'src/app/services/api/base-api.service';
import { ResType } from 'src/app/shared/enum';
import { ModalService } from 'src/app/services/common/modal.service';

/**
 * Service for interacting with the role endpoints of the API
 */
@Injectable({
  providedIn: 'root',
})
export class RoleApiService extends BaseApiService {
  rules: Rule[] = [];

  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.ROLE, http, modalService);
  }

  /**
   * Get the data to send to the API when creating or updating a role.
   *
   * @param role The role to get the data for.
   * @returns The data to send to the API.
   */
  get_data(role: Role): any {
    return {
      name: role.name,
      description: role.description,
      organization_id: role.organization_id,
      rules: getIdsFromArray(role.rules),
    };
  }
}
