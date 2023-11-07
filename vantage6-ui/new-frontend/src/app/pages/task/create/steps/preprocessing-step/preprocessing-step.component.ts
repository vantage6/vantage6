import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { MatSelectChange } from '@angular/material/select';
import { floatRegex, integerRegex } from 'src/app/helpers/regex.helper';
import { Select, SelectParameterType } from 'src/app/models/api/algorithm.model';
import { format, parse } from 'date-fns';

@Component({
  selector: 'app-preprocessing-step',
  templateUrl: './preprocessing-step.component.html',
  styleUrls: ['./preprocessing-step.component.scss']
})
export class PreprocessingStepComponent {
  selectParameterType = SelectParameterType;

  @Input() form!: FormArray;
  @Input() functions: Select[] = [];
  @Input() columns: string[] = [];
  @Output() onFirstPreprocessor: EventEmitter<boolean> = new EventEmitter();
  selectedFunctions: Array<Select | null> = [];

  constructor(private fb: FormBuilder) {}

  get formGroups(): FormGroup[] {
    //Helps getting typed form groups in template
    return this.form.controls as FormGroup[];
  }

  getSelectedFunction(index: number): Select | null {
    return this.selectedFunctions.length >= index ? this.selectedFunctions[index] : null;
  }

  clear(): void {
    this.form.clear();
    this.selectedFunctions = [];
  }

  addPreprocessor(): void {
    if (this.columns.length === 0) {
      this.onFirstPreprocessor.emit();
    }
    this.selectedFunctions.push(null);
    const preprocessorForm = this.fb.nonNullable.group({
      functionID: ['', Validators.required]
    });
    this.form.push(preprocessorForm);
  }

  handleFunctionChange(event: MatSelectChange, index: number): void {
    const formGroup = this.form.controls[index] as FormGroup;

    const controlsToRemove = Object.keys(formGroup.controls).filter((_) => _ !== 'functionID');
    controlsToRemove.forEach((control) => {
      formGroup.removeControl(control);
    });

    const selectedFunction = this.functions.find((_) => _.function === event.value) || null;
    if (selectedFunction) {
      selectedFunction.parameters.forEach((parameter) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const newControl = new FormControl<any>(null);

        //Set default value
        if (parameter.default) {
          if (parameter.type === SelectParameterType.Date) {
            if (parameter.default === 'today') {
              newControl.setValue(format(new Date(), 'yyyy-MM-dd'));
            } else {
              newControl.setValue(format(parse(parameter.default as string, 'yyyy-MM-dd', new Date()), 'yyyy-MM-dd'));
            }
          } else {
            newControl.setValue(parameter.default);
          }
        }

        //Set validators
        if (parameter.required) {
          newControl.addValidators(Validators.required);
        }
        if (parameter.type === SelectParameterType.Integer) {
          newControl.addValidators(Validators.pattern(integerRegex));
        } else if (parameter.type === SelectParameterType.Float) {
          newControl.addValidators(Validators.pattern(floatRegex));
        }
        formGroup.addControl(parameter.name, newControl);
      });
    }
    this.selectedFunctions[index] = selectedFunction;
  }

  deletePreprocessor(index: number): void {
    this.form.removeAt(index);
    this.selectedFunctions.splice(index, 1);
  }

  reset(): void {
    this.selectedFunctions = [];
  }
}
