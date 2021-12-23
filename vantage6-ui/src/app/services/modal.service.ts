import { ComponentType } from '@angular/cdk/portal';
import { Component, Injectable } from '@angular/core';
import {
  NgbModal,
  NgbModalOptions,
  NgbModalRef,
} from '@ng-bootstrap/ng-bootstrap';

@Injectable({
  providedIn: 'root',
})
export class ModalService {
  constructor(private modalService: NgbModal) {}

  openModal(modalComponent: any, message = '', keepOpen = false): NgbModalRef {
    let ngbModalOptions: NgbModalOptions = {};
    if (keepOpen) {
      ngbModalOptions = {
        backdrop: 'static',
        keyboard: false,
      };
    }
    const modalRef = this.modalService.open(modalComponent, ngbModalOptions);
    modalRef.componentInstance.message = message;
    return modalRef;
  }
}
