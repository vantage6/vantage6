import { ComponentType } from '@angular/cdk/portal';
import { Component, Injectable } from '@angular/core';
import {
  NgbModal,
  NgbModalOptions,
  NgbModalRef,
} from '@ng-bootstrap/ng-bootstrap';
import { Role } from 'src/app/role/interfaces/role';
import { User } from 'src/app/user/interfaces/user';
import { ModalDeleteComponent } from './modal-delete/modal-delete.component';

@Injectable({
  providedIn: 'root',
})
export class ModalService {
  constructor(private modalService: NgbModal) {}

  openMessageModal(
    modalComponent: any,
    messages: string[] = [],
    go_back_after_close: boolean = false,
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
    modalRef.componentInstance.messages = messages;
    modalRef.componentInstance.go_back_after_close = go_back_after_close;
    return modalRef;
  }

  openDeleteModal(obj_to_delete: User | Role): NgbModalRef {
    const modalRef = this.modalService.open(ModalDeleteComponent, {});
    modalRef.componentInstance.obj_to_delete = obj_to_delete;
    return modalRef;
  }
}
