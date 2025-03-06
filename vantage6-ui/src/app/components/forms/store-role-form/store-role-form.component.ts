import { Component, Input, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { takeUntil } from 'rxjs';
import { BaseFormComponent } from '../../admin-base/base-form/base-form.component';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { Rule_, StoreRule } from 'src/app/models/api/rule.model';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { PermissionsMatrixStoreComponent } from '../../permissions-matrix/store/permissions-matrix-store.component';
import { RoleSubmitButtonsComponent } from '../../helpers/role-submit-buttons/role-submit-buttons.component';
import { TranslateModule } from '@ngx-translate/core';
import { MatInput } from '@angular/material/input';

@Component({
  selector: 'app-store-role-form',
  templateUrl: './store-role-form.component.html',
  styleUrl: './store-role-form.component.scss',
  imports: [ReactiveFormsModule, MatFormField, MatLabel, MatInput, PermissionsMatrixStoreComponent, RoleSubmitButtonsComponent, TranslateModule]
})
export class StoreRoleFormComponent extends BaseFormComponent implements OnInit {
  @Input() selectableRules: StoreRule[] = [];
  store: AlgorithmStore | null = null;
  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: ''
  });
  selectedRules: number[] = [];

  constructor(
    private fb: FormBuilder,
    private chosenStoreService: ChosenStoreService
  ) {
    super();
  }
  async ngOnInit(): Promise<void> {
    this.chosenStoreService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isInitialized) => {
        if (isInitialized) {
          this.initData();
        }
      });
  }
  private async initData() {
    this.store = this.chosenStoreService.store$.value;
    this.isLoading = false;
  }

  override handleSubmit() {
    if (this.form.valid) {
      this.submitted.emit({ ...this.form.getRawValue(), rules: this.selectedRules });
    }
  }

  handleChangedSelection(rules: Rule_[]): void {
    // we know that these are vantage6 server rules, not store rules here
    rules = rules as StoreRule[];
    this.selectedRules = rules ? rules.map((rule) => rule.id) : [];
  }

  get submitDisabled(): boolean {
    return this.selectedRules?.length === 0;
  }
}
