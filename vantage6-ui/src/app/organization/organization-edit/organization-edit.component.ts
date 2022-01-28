import { Component, OnInit } from '@angular/core';
import { Location } from '@angular/common';

import {
  EMPTY_ORGANIZATION,
  Organization,
} from 'src/app/interfaces/organization';

import { OrganizationService } from 'src/app/services/api/organization.service';
import { OrganizationEditService } from '../organization-edit.service';
import { ModalService } from 'src/app/modal/modal.service';
import { ModalMessageComponent } from 'src/app/modal/modal-message/modal-message.component';

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

  constructor(
    private location: Location,
    private organizationService: OrganizationService,
    private organizationEditService: OrganizationEditService,
    private modalService: ModalService
  ) {}

  ngOnInit(): void {
    this.organizationEditService.getOrganization().subscribe((org) => {
      this.organization = org;
    });
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
