import { Component, OnInit, Input } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { UtilsService } from 'src/app/services/common/utils.service';

@Component({
  selector: 'app-modal-message',
  templateUrl: './modal-message.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './modal-message.component.scss',
  ],
})
export class ModalMessageComponent implements OnInit {
  @Input() messages: string[] = [];
  @Input() go_back_after_close: boolean = false;

  constructor(
    public activeModal: NgbActiveModal,
    private utilsService: UtilsService
  ) {}

  ngOnInit(): void {}

  closeModal(): void {
    this.activeModal.close();
    if (this.go_back_after_close) {
      this.utilsService.goToPreviousPage();
    }
  }
}
