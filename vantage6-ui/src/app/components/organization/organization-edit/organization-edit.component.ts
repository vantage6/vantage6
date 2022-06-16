import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import {
  EMPTY_ORGANIZATION,
  getEmptyOrganization,
  Organization,
} from 'src/app/interfaces/organization';

import { ApiOrganizationService } from 'src/app/services/api/api-organization.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ResType } from 'src/app/shared/enum';
import { UtilsService } from 'src/app/services/common/utils.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { BaseEditComponent } from 'src/app/components/base/base-edit/base-edit.component';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';

@Component({
  selector: 'app-organization-edit',
  templateUrl: './organization-edit.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './organization-edit.component.scss',
  ],
})
export class OrganizationEditComponent
  extends BaseEditComponent
  implements OnInit
{
  organization: Organization = getEmptyOrganization();

  constructor(
    protected router: Router,
    protected activatedRoute: ActivatedRoute,
    protected orgApiService: ApiOrganizationService,
    protected orgDataService: OrgDataService,
    protected modalService: ModalService,
    protected utilsService: UtilsService,
    public userPermission: UserPermissionService
  ) {
    super(
      router,
      activatedRoute,
      userPermission,
      utilsService,
      orgApiService,
      orgDataService,
      modalService
    );
  }

  async init(): Promise<void> {
    // subscribe to id parameter in route to change edited organization if
    // required
    this.activatedRoute.paramMap.subscribe((params) => {
      let id = this.utilsService.getId(params, ResType.ORGANIZATION);
      if (id === EMPTY_ORGANIZATION.id) {
        return; // cannot get organization
      }
      this.setupEdit(id);
    });
  }

  async setupEdit(id: number) {
    let org = await this.orgDataService.get(id);
    if (org) {
      this.organization = org;
    }
  }

  setupCreate(): void {
    // nothing has to be done here for organizations - just implementing
    // abstract base function
  }

  save(): void {
    super.save(this.organization, 'organization');
  }
}
