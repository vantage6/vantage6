import { Component, OnInit } from '@angular/core';
import { Location } from '@angular/common';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';

import {
  EMPTY_ORGANIZATION,
  Organization,
} from 'src/app/interfaces/organization';

import { OrganizationService } from 'src/app/services/api/organization.service';
import { OrganizationEditService } from '../organization-edit.service';
import { ModalService } from 'src/app/modal/modal.service';
import { ModalMessageComponent } from 'src/app/modal/modal-message/modal-message.component';
import { take } from 'rxjs/operators';
import { parseId } from 'src/app/utils';

@Component({
  selector: 'app-organization-edit',
  templateUrl: './organization-edit.component.html',
  styleUrls: [
    '../../globals/buttons.scss',
    './organization-edit.component.scss',
  ],
})
export class OrganizationEditComponent implements OnInit {
  organization: Organization = EMPTY_ORGANIZATION;
  id: number = -1;

  constructor(
    private location: Location,
    private router: Router,
    private activatedRoute: ActivatedRoute,
    private organizationService: OrganizationService,
    private organizationEditService: OrganizationEditService,
    private modalService: ModalService
  ) {}

  ngOnInit(): void {
    this.init();
  }

  async init(): Promise<void> {
    // try to see if organization is already passed from organizationEditService
    this.organizationEditService
      .getOrganization()
      .pipe(take(1))
      .subscribe((org) => {
        this.organization = org;
        this.id = this.organization.id;
      });

    // subscribe to id parameter in route to change edited organization if
    // required
    this.activatedRoute.paramMap.subscribe((params) => {
      let new_id = this.getId(params);
      if (new_id === EMPTY_ORGANIZATION.id) {
        return; // cannot get organization
      }
      if (new_id !== this.id) {
        this.id = new_id;
        this.setOrgFromAPI(new_id);
      }
    });
  }

  getId(params: ParamMap): number {
    if (this.router.url.endsWith('create')) {
      return EMPTY_ORGANIZATION.id;
    }
    // we are editing an organization: get the organization id
    let new_id = parseId(params.get('id'));
    if (isNaN(new_id)) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        "The organization id '" +
          params.get('id') +
          "' cannot be parsed. Please provide a valid organization id",
      ]);
      return EMPTY_ORGANIZATION.id;
    }
    return new_id;
  }

  async setOrgFromAPI(id: number): Promise<void> {
    this.organization = await this.organizationService.getOrganization(id);
  }

  saveEdit(): void {
    let request;
    if (this.organization.is_being_created) {
      request = this.organizationService.create(this.organization);
    } else {
      request = this.organizationService.update(this.organization);
    }

    request.subscribe(
      (data) => {
        this.goBack();
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
    this.goBack();
  }

  goBack(): void {
    // go back to previous page
    this.location.back();
  }
}
