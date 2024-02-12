import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { AlgorithmStore, AlgorithmStoreForm } from 'src/app/models/api/algorithmStore.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { PermissionService } from 'src/app/services/permission.service';

@Component({
  selector: 'app-algorithm-store-form',
  templateUrl: './algorithm-store-form.component.html',
  styleUrls: ['./algorithm-store-form.component.scss']
})
export class AlgorithmStoreFormComponent implements OnInit, OnDestroy {
  @Input() algorithmStore?: AlgorithmStore;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<AlgorithmStoreForm> = new EventEmitter();

  form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    algorithm_store_url: ['', Validators.required],
    server_url: ['', Validators.required],
    collaboration_id: '',
    all_collaborations: false
  });
  destroy$ = new Subject();
  canSetAllCollaborations = false;

  constructor(
    private router: Router,
    private fb: FormBuilder,
    private permissionService: PermissionService
  ) {}

  ngOnInit(): void {
    this.setPermissions();
    if (this.algorithmStore) {
      this.form.controls.name.setValue(this.algorithmStore.name);
      this.form.controls.algorithm_store_url.setValue(this.algorithmStore.url);
    }
    // get ID from router
    this.form.controls.collaboration_id.setValue(this.router.url.split('/').pop() as string);
  }

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

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canSetAllCollaborations = this.permissionService.isAllowed(ScopeType.GLOBAL, ResourceType.COLLABORATION, OperationType.EDIT);
        }
      });
  }
}
