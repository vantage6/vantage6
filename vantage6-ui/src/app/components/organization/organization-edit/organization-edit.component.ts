import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import {
  EMPTY_ORGANIZATION,
  Organization,
} from 'src/app/interfaces/organization';

import { ApiOrganizationService } from 'src/app/services/api/api-organization.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';
import { take } from 'rxjs/operators';
import { ResType } from 'src/app/shared/enum';
import { UtilsService } from 'src/app/services/common/utils.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';

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
    private utilsService: UtilsService,
    private convertJsonService: ConvertJsonService
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
    return (
      await this.orgDataService.get(id, this.convertJsonService.getOrganization)
    )
      .pipe(take(1))
      .subscribe((org: Organization) => {
        this.organization = org;
      });
  }

  saveEdit(): void {
    let request;
    if (this.organization.id == EMPTY_ORGANIZATION.id) {
      request = this.orgApiService.create(this.organization);
    } else {
      request = this.orgApiService.update(this.organization);
    }

    request.subscribe(
      (new_org) => {
        this.orgDataService.add(new_org);
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
