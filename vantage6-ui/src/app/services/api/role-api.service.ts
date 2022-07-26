import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';

import { getIdsFromArray } from 'src/app/shared/utils';
import { ApiService } from 'src/app/services/api/api.service';
import { ResType } from 'src/app/shared/enum';
import { ModalService } from 'src/app/services/common/modal.service';

@Injectable({
  providedIn: 'root',
})
export class RoleApiService extends ApiService {
  rules: Rule[] = [];

  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.ROLE, http, modalService);
  }

  get_data(role: Role): any {
    return {
      name: role.name,
      description: role.description,
      organization_id: role.organization_id,
      rules: getIdsFromArray(role.rules),
    };
  }
}
