import { Injectable } from '@angular/core';
import { Router, ParamMap } from '@angular/router';

import { ModalService } from '../modal/modal.service';

import { ModalMessageComponent } from '../modal/modal-message/modal-message.component';
import { parseId } from '../utils';

@Injectable({
  providedIn: 'root',
})
export class UtilsService {
  constructor(private router: Router, private modalService: ModalService) {}

  getId(params: ParamMap, resource: string): number {
    if (this.router.url.endsWith('create')) {
      return -1;
    }
    // we are editing an organization: get the organization id
    let new_id = parseId(params.get('id'));
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
}
