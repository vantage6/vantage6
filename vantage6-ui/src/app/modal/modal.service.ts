import { ComponentType } from '@angular/cdk/portal';
import { Component, Injectable } from '@angular/core';
import {
  NgbModal,
  NgbModalOptions,
  NgbModalRef,
} from '@ng-bootstrap/ng-bootstrap';
import { Role } from '../interfaces/role';
import { User } from '../interfaces/user';
import { ModalDeleteComponent } from './modal-delete/modal-delete.component';

@Injectable({
  providedIn: 'root',
})
export class ModalService {
  constructor(private modalService: NgbModal) {}

  openMessageModal(
    modalComponent: any,
    message = '',
    keepOpen = false
  ): NgbModalRef {
    let options: NgbModalOptions = {};
    if (keepOpen) {
      options = {
        backdrop: 'static',
        keyboard: false,
      };
    }
    const modalRef = this.modalService.open(modalComponent, options);
    modalRef.componentInstance.message = message;
    return modalRef;
  }

  openDeleteModal(obj_to_delete: User | Role): NgbModalRef {
    const modalRef = this.modalService.open(ModalDeleteComponent, {});
    modalRef.componentInstance.obj_to_delete = obj_to_delete;
    return modalRef;
  }
}
