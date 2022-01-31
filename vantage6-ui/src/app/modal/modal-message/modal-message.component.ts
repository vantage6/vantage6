import { Component, OnInit, Input } from '@angular/core';
import { Location } from '@angular/common';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'app-modal-message',
  templateUrl: './modal-message.component.html',
  styleUrls: ['./modal-message.component.scss'],
})
export class ModalMessageComponent implements OnInit {
  @Input() messages: string[] = [];
  @Input() go_back_after_close: boolean = false;

  constructor(public activeModal: NgbActiveModal, private location: Location) {}

  ngOnInit(): void {}

  closeModal(): void {
    this.activeModal.close();
    if (this.go_back_after_close) {
      this.goBack();
    }
  }

  goBack(): void {
    // go back to previous page
    this.location.back();
  }
}
