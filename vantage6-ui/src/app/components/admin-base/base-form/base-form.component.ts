import { Component, EventEmitter, OnDestroy, Output } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Subject } from 'rxjs';
import { ResourceForm } from 'src/app/models/api/resource.model';

@Component({
  selector: 'app-base-form',
  templateUrl: './base-form.component.html',
  styleUrl: './base-form.component.scss'
})
export abstract class BaseFormComponent implements OnDestroy {
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<ResourceForm> = new EventEmitter();

  destroy$ = new Subject();

  isEdit: boolean = false;
  isLoading: boolean = true;
  abstract form: FormGroup;

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  handleSubmit() {
    if (this.form.valid) {
      this.submitted.emit(this.form.getRawValue());
    }
  }

  handleCancel() {
    this.cancelled.emit();
  }
}
