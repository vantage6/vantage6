import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-role-submit-buttons',
  templateUrl: './role-submit-buttons.component.html',
  styleUrls: ['./role-submit-buttons.component.scss']
})
export class RoleSubmitButtonsComponent {
  @Input() submitDisabled: boolean = false;
  @Output() submitted: EventEmitter<void> = new EventEmitter();
  @Output() cancelled: EventEmitter<void> = new EventEmitter();

  handleCancel(): void {
    this.cancelled.emit();
  }

  handleSubmit(): void {
    this.submitted.emit();
  }
}
