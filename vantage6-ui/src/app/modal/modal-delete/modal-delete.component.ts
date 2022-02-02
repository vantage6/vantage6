import { Component, Input, OnInit } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ExitMode } from 'src/app/shared/enum';

import { Role } from 'src/app/role/interfaces/role';
import { User } from 'src/app/user/interfaces/user';

@Component({
  selector: 'app-modal-delete',
  templateUrl: './modal-delete.component.html',
  styleUrls: [
    '../../shared/scss/buttons.scss',
    './modal-delete.component.scss',
  ],
})
export class ModalDeleteComponent implements OnInit {
  @Input() obj_to_delete: User | Role | any;

  constructor(public activeModal: NgbActiveModal) {}

  ngOnInit(): void {}

  getDeleteText(): string {
    if ((this.obj_to_delete as User).username) {
      return "the user '" + this.obj_to_delete.username + "'";
    } else if ((this.obj_to_delete as Role).name) {
      return "the role '" + this.obj_to_delete.name + "'";
    }
    return 'this entity';
  }

  cancel(): void {
    this.activeModal.close(ExitMode.CANCEL);
  }

  delete(): void {
    this.activeModal.close(ExitMode.DELETE);
  }
}
