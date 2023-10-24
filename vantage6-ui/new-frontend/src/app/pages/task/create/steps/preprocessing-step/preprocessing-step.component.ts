import { Component, Input } from '@angular/core';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { MatSelectChange } from '@angular/material/select';
import { Select, SelectParameterType } from 'src/app/models/api/algorithm.model';

interface Preprocessor {
  function?: Select;
  formGroup: FormGroup;
}

@Component({
  selector: 'app-preprocessing-step',
  templateUrl: './preprocessing-step.component.html',
  styleUrls: ['./preprocessing-step.component.scss']
})
export class PreprocessingStepComponent {
  selectParameterType = SelectParameterType;

  @Input() form!: FormArray;
  @Input() functions: Select[] = [];
  selectedFunctions: Array<Select | null> = [];
  columns: string[] = ['Column 1', 'Column 2', 'Column 3']; //TODO: Get column data from backend, when backend is ready

  constructor(private fb: FormBuilder) {}

  get formGroups(): FormGroup[] {
    return this.form.controls as FormGroup[];
  }

  getSelectedFunction(index: number): Select | null {
    return this.selectedFunctions.length >= index ? this.selectedFunctions[index] : null;
  }

  addPreprocessor(): void {
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
        const newControl = new FormControl(parameter.default || null);
        if (parameter.required) {
          newControl.setValidators(Validators.required);
        }
        formGroup.addControl(parameter.name, newControl);
      });
    }
    this.selectedFunctions[index] = selectedFunction;
  }

  reset(): void {
    this.selectedFunctions = [];
  }
}
