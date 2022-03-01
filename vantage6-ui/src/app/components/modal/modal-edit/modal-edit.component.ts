import { Component, Input, OnInit } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ModalService } from 'src/app/services/common/modal.service';
import { ExitMode } from 'src/app/shared/enum';

@Component({
  selector: 'app-modal-edit',
  templateUrl: './modal-edit.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './modal-edit.component.scss',
  ],
})
export class ModalEditComponent implements OnInit {
  @Input() param_name: string = '';
  @Input() current_value: string = '';
  new_value: string = '';

  constructor(
    public activeModal: NgbActiveModal,
    private modalService: ModalService
  ) {}

  ngOnInit(): void {}

  cancel(): void {
    this.activeModal.close({ exitMode: ExitMode.CANCEL });
  }

  edit(): void {
    this.activeModal.close({
      exitMode: ExitMode.EDIT,
      new_value: this.new_value,
    });
  }
}
