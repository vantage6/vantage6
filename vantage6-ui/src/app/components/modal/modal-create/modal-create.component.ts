import { Component, Input, OnInit } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

import { ExitMode } from 'src/app/shared/enum';
import { Node } from 'src/app/interfaces/node';

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
  @Input() offline_nodes: Node[] = [];

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

  // TODO the functions below are duplicates from organization component
  // Refactor them
  getNodeButtonText(node: Node): string {
    const online_text = node.is_online ? ' (online)' : ' (offline)';
    return node.name + online_text;
  }

  getButtonClasses(node: Node): string {
    let default_classes = 'mat-button btn-link inline ';
    if (node.is_online) return default_classes + 'btn-online';
    else return default_classes + 'btn-offline';
  }
}
