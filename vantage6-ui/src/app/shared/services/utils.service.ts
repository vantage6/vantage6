import { Injectable } from '@angular/core';
import { Router, ParamMap } from '@angular/router';
import { Location } from '@angular/common';

import { ModalService } from 'src/app/modal/modal.service';

import { ModalMessageComponent } from 'src/app/modal/modal-message/modal-message.component';
import { parseId } from 'src/app/shared/utils';
import { OpsType, ResType } from '../enum';

@Injectable({
  providedIn: 'root',
})
export class UtilsService {
  constructor(
    private router: Router,
    private location: Location,
    private modalService: ModalService
  ) {}

  getId(
    params: ParamMap,
    resource: ResType,
    param_name: string = 'id'
  ): number {
    if (this.router.url.includes(OpsType.CREATE) && param_name === 'id') {
      return -1;
    }
    // we are editing an organization: get the organization id
    let new_id = parseId(params.get(param_name));
    if (isNaN(new_id)) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'The ' +
          resource +
          " id '" +
          params.get('id') +
          "' cannot be parsed. Please provide a valid " +
          resource +
          ' id',
      ]);
      return -1;
    }
    return new_id;
  }

  goToPreviousPage(): void {
    // go back to previous page
    this.location.back();
  }
}
