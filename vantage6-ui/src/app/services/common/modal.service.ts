import { Injectable } from '@angular/core';
import {
  NgbModal,
  NgbModalOptions,
  NgbModalRef,
} from '@ng-bootstrap/ng-bootstrap';
import { Role } from 'src/app/interfaces/role';
import { User } from 'src/app/interfaces/user';
import { ModalDeleteComponent } from 'src/app/components/modal/modal-delete/modal-delete.component';
import { ModalEditComponent } from 'src/app/components/modal/modal-edit/modal-edit.component';

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

  openEditModal(param_name: string, current_value: string): NgbModalRef {
    const modalRef = this.modalService.open(ModalEditComponent, {});
    modalRef.componentInstance.param_name = param_name;
    modalRef.componentInstance.current_value = current_value;
    return modalRef;
  }

  openDeleteModal(
    obj_to_delete: User | Role,
    extra_message: string | null = null
  ): NgbModalRef {
    const modalRef = this.modalService.open(ModalDeleteComponent, {});
    modalRef.componentInstance.obj_to_delete = obj_to_delete;
    modalRef.componentInstance.extra_message = extra_message;
    return modalRef;
  }
}
