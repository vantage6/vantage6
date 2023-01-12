import { Component, Input, OnInit } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ExitMode } from 'src/app/shared/enum';

@Component({
  selector: 'app-modal-create',
  templateUrl: './modal-create.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './modal-create.component.scss',
  ],
})
export class ModalCreateComponent implements OnInit {
  @Input() messages: string[] = [];

  constructor(public activeModal: NgbActiveModal) {}

  ngOnInit(): void {}

  cancel(): void {
    this.activeModal.close({ exitMode: ExitMode.CANCEL });
  }

  create(): void {
    this.activeModal.close({
      exitMode: ExitMode.CREATE,
    });
  }
}
