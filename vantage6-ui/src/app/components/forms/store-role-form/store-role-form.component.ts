import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { takeUntil } from 'rxjs';
import { StoreRoleService } from 'src/app/services/store-role.service';
import { BaseFormComponent } from '../../admin-base/base-form/base-form.component';
import { StoreRole } from 'src/app/models/api/store-role.model';
import { ChosenStoreService } from 'src/app/services/chosen-store.service';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { Rule_, StoreRule } from 'src/app/models/api/rule.model';

@Component({
  selector: 'app-store-role-form',
  templateUrl: './store-role-form.component.html',
  styleUrl: './store-role-form.component.scss'
})
export class StoreRoleFormComponent extends BaseFormComponent implements OnInit {
  @Input() selectableRules: StoreRule[] = [];
  store: AlgorithmStore | null = null;
  

  constructor(private fb: FormBuilder, private chosenStoreService: ChosenStoreService) {
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

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: '',
  });

  selectedRules: number[] = [];

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
