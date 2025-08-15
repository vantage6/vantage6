import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { FormGroup, FormArray, FormBuilder, AbstractControl, Validators } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { Argument, ArgumentType, AlgorithmFunction, ConditionalArgComparatorType } from '../../../../../models/api/algorithm.model';
import { BaseOrganization } from '../../../../../models/api/organization.model';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { NgIf, NgFor } from '@angular/common';
import { AlertComponent } from '../../../../alerts/alert/alert.component';
import { NumberOnlyDirective } from '../../../../../directives/numberOnly.directive';
import { floatRegex, integerRegex } from '../../../../../helpers/regex.helper';
import { isTruthy } from '../../../../../helpers/utils.helper';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { readFile } from 'src/app/helpers/file.helper';
import { ChangesInCreateTaskService } from 'src/app/services/changes-in-create-task.service';
import { BaseSession } from 'src/app/models/api/session.models';

@Component({
  selector: 'app-parameter-step',
  templateUrl: './parameter-step.component.html',
  styleUrls: ['./parameter-step.component.scss'],
  imports: [
    TranslateModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatSelectModule,
    MatInputModule,
    MatButtonModule,
    MatCheckboxModule,
    MatIconModule,
    NgIf,
    NgFor,
    MatProgressSpinner,
    AlertComponent,
    NumberOnlyDirective
  ],
  standalone: true
})
export class ParameterStepComponent implements OnInit, OnDestroy {
  @Input() formGroup!: FormGroup;
  @Input() function: AlgorithmFunction | null = null;
  @Input() columns: string[] = [];
  @Input() isLoadingColumns = false;
  @Input() argumentType = ArgumentType;

  @Output() jsonFileSelected = new EventEmitter<{ event: Event; argument: Argument }>();
  @Output() addInputFieldRequested = new EventEmitter<Argument>();
  @Output() removeInputFieldRequested = new EventEmitter<{ argument: Argument; index: number }>();

  organizations: BaseOrganization[] = [];

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private changesInCreateTaskService: ChangesInCreateTaskService
  ) {}

  ngOnInit(): void {
    this.setupFormListeners();
    this.setupChangeListeners();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private setupFormListeners(): void {
    // Listen to changes in all parameter form controls
    if (this.function?.arguments) {
      this.function.arguments.forEach((argument: Argument) => {
        if (this.formGroup.controls[argument.name]) {
          this.formGroup.controls[argument.name].valueChanges.pipe(takeUntil(this.destroy$)).subscribe((value: any) => {
            // Handle parameter value changes if needed
          });
        }
      });
    }
  }

  private setupChangeListeners(): void {
    this.changesInCreateTaskService.organizationChange$.pipe(takeUntil(this.destroy$)).subscribe((organizations) => {
      this.organizations = organizations;
    });
    this.changesInCreateTaskService.sessionChange$.pipe(takeUntil(this.destroy$)).subscribe((session) => {
      this.onSessionChange(session);
    });
  }

  onSessionChange(session: BaseSession | null): void {
    if (!session) return;
    // if session changes, the function is also cleared. Therefore, we also need to
    // clear the parameters
    this.clearForm();
  }

  clearForm(): void {
    this.formGroup.reset();
  }

  onJsonFileSelected(event: Event, argument: Argument): void {
    this.jsonFileSelected.emit({ event, argument });
  }

  onAddInputField(argument: Argument): void {
    this.addInputFieldRequested.emit(argument);
  }

  onRemoveInputField(argument: Argument, index: number): void {
    this.removeInputFieldRequested.emit({ argument, index });
  }

  // Helper methods for determining what to show
  shouldDisplayArgument(function_: AlgorithmFunction | null, argument: Argument): boolean {
    // argument should not be displayed if it is conditional on another and the
    // condition is not fulfilled
    if (!argument.conditional_on_id) {
      return true;
    }
    const conditionalArg = function_?.arguments.find((arg: Argument) => arg.id === argument.conditional_on_id);
    if (!conditionalArg) {
      return true;
    }
    let curConditionalValue = this.formGroup.get(conditionalArg.name)?.value;
    // cast the values (if necessary)
    let conditionDatabaseValue: string | number | boolean | undefined;
    if (conditionalArg.type === ArgumentType.Boolean) {
      conditionDatabaseValue = isTruthy(argument.conditional_value);
      curConditionalValue = isTruthy(curConditionalValue);
    } else if (conditionalArg.type === ArgumentType.Float || conditionalArg.type === ArgumentType.Integer) {
      conditionDatabaseValue = Number(argument.conditional_value);
      curConditionalValue = Number(curConditionalValue);
    } else {
      conditionDatabaseValue = argument.conditional_value;
    }
    // evaluate the condition
    if (argument.conditional_operator === ConditionalArgComparatorType.Equal) {
      return conditionDatabaseValue === curConditionalValue;
    } else if (argument.conditional_operator === ConditionalArgComparatorType.NotEqual) {
      return conditionDatabaseValue !== curConditionalValue;
    } else if (conditionDatabaseValue) {
      if (argument.conditional_operator === ConditionalArgComparatorType.GreaterThan) {
        return conditionDatabaseValue > curConditionalValue;
      } else if (argument.conditional_operator === ConditionalArgComparatorType.GreaterThanOrEqual) {
        return conditionDatabaseValue >= curConditionalValue;
      } else if (argument.conditional_operator === ConditionalArgComparatorType.LessThan) {
        return conditionDatabaseValue < curConditionalValue;
      } else if (argument.conditional_operator === ConditionalArgComparatorType.LessThanOrEqual) {
        return conditionDatabaseValue <= curConditionalValue;
      }
    }
    // fallback - just display it, but should never get here
    return true;
  }

  shouldIncludeFormField(argument: Argument): boolean {
    return (
      !this.shouldShowParameterJsonInput(argument) &&
      !this.shouldShowParameterBooleanInput(argument) &&
      !this.shouldShowMultipleInput(argument)
    );
  }

  shouldShowColumnDropdown(argument: Argument): boolean {
    return argument.type === ArgumentType.Column || argument.type === ArgumentType.ColumnList;
  }

  shouldShowAllowedValuesDropdown(argument: Argument): boolean {
    return (argument.allowed_values?.length ?? 0) > 0;
  }

  shouldShowOrganizationDropdown(argument: Argument): boolean {
    return argument.type === ArgumentType.Organization || argument.type === ArgumentType.OrganizationList;
  }

  shouldShowParameterSimpleInput(argument: Argument): boolean {
    return (
      !this.shouldShowColumnDropdown(argument) &&
      !this.shouldShowOrganizationDropdown(argument) &&
      !this.shouldShowParameterBooleanInput(argument) &&
      !this.shouldShowParameterJsonInput(argument) &&
      !this.shouldShowAllowedValuesDropdown(argument)
    );
  }

  shouldShowParameterJsonInput(argument: Argument): boolean {
    return argument.type === ArgumentType.Json;
  }

  shouldShowParameterBooleanInput(argument: Argument): boolean {
    return argument.type === ArgumentType.Boolean;
  }

  shouldShowMultipleInput(argument: Argument): boolean {
    return (
      argument.type === ArgumentType.StringList || argument.type === ArgumentType.IntegerList || argument.type === ArgumentType.FloatList
    );
  }

  isFirstDatabaseMultiple(): boolean {
    return this.function?.databases?.[0] ? this.function.databases[0].multiple || false : false;
  }

  containsColumnArguments(): boolean {
    return this.function?.arguments.some((arg) => arg.type === ArgumentType.Column || arg.type === ArgumentType.ColumnList) || false;
  }

  sortArgumentsForDisplay(arguments_: Argument[] | undefined) {
    if (!arguments_) return undefined;
    // first order by ID
    arguments_ = arguments_.sort((a, b) => a.id - b.id);
    // Sort the parameters of the function such that parameters that are conditional on
    // others are just behind those
    for (let idx = 0; idx < arguments_.length; idx++) {
      const arg = arguments_[idx];
      if (arg?.conditional_on_id) {
        // Find the idx in the list of the one it is conditional on
        const conditionalIdx = arguments_.findIndex((condArg) => condArg.id === arg.conditional_on_id);
        if (conditionalIdx > idx) {
          [arguments_[idx], arguments_[conditionalIdx]] = [arguments_[conditionalIdx], arguments_[idx]];
          idx = -1;
        }
      }
    }
    return arguments_;
  }

  getDisplayName(obj: AlgorithmFunction | Argument): string {
    return obj.display_name && obj.display_name != '' ? obj.display_name : obj.name;
  }

  getJsonFileName(argument: Argument): string {
    return this.formGroup.controls[`${argument.name}_jsonFileName`]?.value || '';
  }

  getFormArrayControls(argument: Argument): AbstractControl[] {
    if ((this.formGroup.get(argument.name) as FormArray).controls === undefined) {
      const initialControl = argument.has_default_value ? [] : [this.getNewControlForArgumentList(argument)];
      this.formGroup.setControl(argument.name, this.fb.array(initialControl));
    }
    return (this.formGroup.get(argument.name) as FormArray).controls;
  }

  private getNewControlForArgumentList(argument: Argument): AbstractControl {
    if (argument.type === this.argumentType.IntegerList) {
      return this.fb.control('', [Validators.required, Validators.pattern(integerRegex)]);
    } else if (argument.type === this.argumentType.FloatList) {
      return this.fb.control('', [Validators.required, Validators.pattern(floatRegex)]);
    } else {
      return this.fb.control('', Validators.required);
    }
  }

  compareIDsForSelection(id1: number | string, id2: number | string | string[]): boolean {
    // The mat-select object set from typescript only has an ID set. Compare that with the ID of the
    // organization object from the collaboration
    if (Array.isArray(id2)) {
      id2 = id2[0];
    }
    if (typeof id1 === 'number') {
      id1 = id1.toString();
    }
    if (typeof id2 === 'number') {
      id2 = id2.toString();
    }
    return id1 === id2;
  }

  // Functions needed for parameter step event handlers
  async selectedJsonFile(event: Event, argument: Argument): Promise<void> {
    const selectedFile = (event.target as HTMLInputElement).files?.item(0) || null;

    if (!selectedFile) return;
    const fileData = await readFile(selectedFile);

    this.formGroup.controls[`${argument.name}`].setValue(fileData || '');
    this.formGroup.controls[`${argument.name}_jsonFileName`].setValue(selectedFile.name || '');
  }

  addInputFieldForArg(argument: Argument): void {
    (this.formGroup.get(argument.name) as FormArray).push(this.getNewControlForArgumentList(argument));
  }

  removeInputFieldForArg(argument: Argument, index: number): void {
    (this.formGroup.get(argument.name) as FormArray).removeAt(index);
  }
}
