import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { AlgorithmFunction, AlgorithmFunctionExtended, Argument, Algorithm } from '../../../../../models/api/algorithm.model';
import { BaseOrganization } from '../../../../../models/api/organization.model';
import { AlgorithmStepType } from '../../../../../models/api/session.models';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { NgIf, NgFor } from '@angular/common';
import { AlertComponent } from '../../../../alerts/alert/alert.component';
import { HighlightedTextPipe } from '../../../../../pipes/highlighted-text.pipe';
import { Collaboration } from 'src/app/models/api/collaboration.model';

@Component({
  selector: 'app-function-step',
  templateUrl: './function-step.component.html',
  styleUrls: ['./function-step.component.scss'],
  imports: [
    TranslateModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatSelectModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    NgIf,
    NgFor,
    AlertComponent,
    HighlightedTextPipe
  ],
  standalone: true
})
export class FunctionStepComponent implements OnInit, OnDestroy {
  @Input() formGroup!: FormGroup;
  @Input() functionsFilteredBySearch: AlgorithmFunctionExtended[] = [];
  @Input() organizations: BaseOrganization[] = [];
  @Input() function: AlgorithmFunctionExtended | null = null;
  @Input() sessionRestrictedToSameImage = false;
  @Input() showWarningUniqueDFName = false;
  @Input() node: any = null;
  @Input() algorithms: Algorithm[] = [];
  @Input() collaboration: Collaboration | null | undefined = null;

  @Output() functionSelected = new EventEmitter<{ functionName: string; algorithmID: number; algorithmStoreID: number }>();
  @Output() searchRequested = new EventEmitter<void>();
  @Output() searchCleared = new EventEmitter<void>();

  readonly algorithmStepType = AlgorithmStepType;

  private destroy$ = new Subject<void>();

  constructor() {}

  ngOnInit(): void {
    this.setupFormListeners();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private setupFormListeners(): void {
    this.formGroup.controls['algorithmFunctionSpec'].valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe((algorithmFunctionSpec: string) => {
        if (algorithmFunctionSpec) {
          const [functionName, algorithmID, algorithmStoreID] = algorithmFunctionSpec.split('__');
          this.functionSelected.emit({
            functionName: String(functionName),
            algorithmID: Number(algorithmID),
            algorithmStoreID: Number(algorithmStoreID)
          });
        }
      });
  }

  onSearch(): void {
    this.searchRequested.emit();
  }

  onClearSearch(): void {
    this.searchCleared.emit();
  }

  isFederatedStep(stepType: AlgorithmStepType): boolean {
    return stepType !== AlgorithmStepType.CentralCompute;
  }

  isDataExtractionStep(): boolean {
    return this.function?.step_type === AlgorithmStepType.DataExtraction;
  }

  getFunctionOptionLabel(func: AlgorithmFunctionExtended): string {
    const curAlgorithm = this.algorithms.find((_) => _.id === func.algorithm_id && _.algorithm_store_id == func.algorithm_store_id);
    const storeName = curAlgorithm ? this.getAlgorithmStoreName(curAlgorithm) : '';
    return `${this.getDisplayName(func)} <div class="detail-txt"> | ${func.algorithm_name}, ${storeName}, ${func.step_type}</div>`;
  }

  getDisplayName(obj: AlgorithmFunction | Argument): string {
    return obj.display_name && obj.display_name != '' ? obj.display_name : obj.name;
  }

  getAlgorithmFunctionSpec(func: AlgorithmFunctionExtended): string {
    return `${func.name}__${func.algorithm_id}__${func.algorithm_store_id}`;
  }

  compareIDsForSelection(option: string, value: string): boolean {
    return option === value;
  }

  getAlgorithmStoreName(algorithm: Algorithm): string {
    if (this.collaboration?.algorithm_stores && this.collaboration.algorithm_stores.length > 1) {
      const store_name = this.collaboration.algorithm_stores.find((_) => _.url === algorithm.algorithm_store_url)?.name;
      if (store_name) {
        return store_name;
      }
    }
    return '';
  }
}
