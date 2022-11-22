import { Component, Input, OnInit } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ExitMode } from 'src/app/shared/enum';

@Component({
  selector: 'app-modal-kill',
  templateUrl: './modal-kill.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './modal-kill.component.scss',
  ],
})
export class ModalKillComponent implements OnInit {
  @Input() id: number;

  constructor(public activeModal: NgbActiveModal) {}

  ngOnInit(): void {}

  cancel(): void {
    this.activeModal.close(ExitMode.CANCEL);
  }

  kill(): void {
    this.activeModal.close(ExitMode.KILL);
  }
}
