import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';

import {
  Collaboration,
  EMPTY_COLLABORATION,
} from '../interfaces/collaboration';

import { UserPermissionService } from 'src/app/auth/services/user-permission.service';

@Component({
  selector: 'app-collaboration-view',
  templateUrl: './collaboration-view.component.html',
  styleUrls: [
    '../../shared/scss/buttons.scss',
    './collaboration-view.component.scss',
  ],
})
export class CollaborationViewComponent implements OnInit {
  @Input() collaboration: Collaboration = EMPTY_COLLABORATION;
  @Output() deletingCollab = new EventEmitter<Collaboration>();
  @Output() editingCollab = new EventEmitter<Collaboration>();

  constructor(public userPermission: UserPermissionService) {}

  ngOnInit(): void {}

  encrypted(): string {
    return this.collaboration.encrypted ? 'Yes' : 'No';
  }
}
