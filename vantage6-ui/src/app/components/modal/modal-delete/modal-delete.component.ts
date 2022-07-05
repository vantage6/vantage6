import { Component, Input, OnInit } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

import { ExitMode, ResType } from 'src/app/shared/enum';

import { Role } from 'src/app/interfaces/role';
import { User } from 'src/app/interfaces/user';
import { Resource } from 'src/app/shared/types';

@Component({
  selector: 'app-modal-delete',
  templateUrl: './modal-delete.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './modal-delete.component.scss',
  ],
})
export class ModalDeleteComponent implements OnInit {
  @Input() to_delete: Resource | Resource[] | undefined;
  @Input() obj_type: ResType | undefined;
  @Input() extra_message: string | null = null;

  constructor(public activeModal: NgbActiveModal) {}

  ngOnInit(): void {}

  getDeleteText(): string {
    if (Array.isArray(this.to_delete)) {
      return `the ${this.to_delete.length} ${this.obj_type}(s) you have selected`;
    } else if ((this.to_delete as User).username) {
      return `the ${this.obj_type} '${(this.to_delete as User).username}'`;
    } else {
      return `the ${this.obj_type} '${(this.to_delete as Role).name}'`;
    }
  }

  cancel(): void {
    this.activeModal.close(ExitMode.CANCEL);
  }

  delete(): void {
    this.activeModal.close(ExitMode.DELETE);
  }
}
