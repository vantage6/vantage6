import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import {
  EMPTY_ORGANIZATION,
  Organization,
} from 'src/app/interfaces/organization';

import { ApiOrganizationService } from 'src/app/services/api/api-organization.service';
import { OrganizationStoreService } from 'src/app/services/store/organization-store.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import { take } from 'rxjs/operators';
import { ResType } from 'src/app/shared/enum';
import { UtilsService } from 'src/app/services/common/utils.service';

@Component({
  selector: 'app-organization-edit',
  templateUrl: './organization-edit.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './organization-edit.component.scss',
  ],
})
export class OrganizationEditComponent implements OnInit {
  organization: Organization = EMPTY_ORGANIZATION;
  id: number = -1;

  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute,
    private organizationService: ApiOrganizationService,
    private organizationStoreService: OrganizationStoreService,
    private modalService: ModalService,
    private utilsService: UtilsService
  ) {}

  ngOnInit(): void {
    this.init();
  }

  async init(): Promise<void> {
    // try to see if organization is already passed from organizationStoreService
    this.organizationStoreService
      .getOrganization()
      .pipe(take(1))
      .subscribe((org) => {
        this.organization = org;
        this.id = this.organization.id;
      });

    // subscribe to id parameter in route to change edited organization if
    // required
    this.activatedRoute.paramMap.subscribe((params) => {
      let new_id = this.utilsService.getId(params, ResType.ORGANIZATION);
      if (new_id === EMPTY_ORGANIZATION.id) {
        return; // cannot get organization
      }
      if (new_id !== this.id) {
        this.id = new_id;
        this.setOrgFromAPI(new_id);
      }
    });
  }

  async setOrgFromAPI(id: number): Promise<void> {
    this.organization = await this.organizationService.getOrganization(id);
  }

  saveEdit(): void {
    let request;
    if (this.organization.id == EMPTY_ORGANIZATION.id) {
      request = this.organizationService.create(this.organization);
    } else {
      request = this.organizationService.update(this.organization);
    }

    request.subscribe(
      (new_org) => {
        this.organizationStoreService.addOrganization(new_org);
        this.router.navigate([`/organization/${new_org.id}`]);
      },
      (error) => {
        this.modalService.openMessageModal(ModalMessageComponent, [
          'Error:',
          error.error.msg,
        ]);
      }
    );
  }

  cancelEdit(): void {
    this.utilsService.goToPreviousPage();
  }
}
