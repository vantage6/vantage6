import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import {
  EMPTY_ORGANIZATION,
  Organization,
} from 'src/app/interfaces/organization';

import { ApiOrganizationService } from 'src/app/services/api/api-organization.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import { ResType } from 'src/app/shared/enum';
import { UtilsService } from 'src/app/services/common/utils.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';

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

  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute,
    private orgApiService: ApiOrganizationService,
    private orgDataService: OrgDataService,
    private modalService: ModalService,
    private utilsService: UtilsService
  ) {}

  ngOnInit(): void {
    this.init();
  }

  async init(): Promise<void> {
    // subscribe to id parameter in route to change edited organization if
    // required
    this.activatedRoute.paramMap.subscribe((params) => {
      let id = this.utilsService.getId(params, ResType.ORGANIZATION);
      if (id === EMPTY_ORGANIZATION.id) {
        return; // cannot get organization
      }
      this.setOrganization(id);
    });
  }

  async setOrganization(id: number) {
    this.organization = await this.orgDataService.get(id);
  }

  saveEdit(): void {
    const is_created: boolean = this.organization.id === EMPTY_ORGANIZATION.id;
    let request;
    if (is_created) {
      request = this.orgApiService.create(this.organization);
    } else {
      request = this.orgApiService.update(this.organization);
    }

    request.subscribe(
      (new_org) => {
        if (is_created) this.orgDataService.save(new_org);
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
