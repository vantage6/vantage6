import { Component, Input } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
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

  @Input() functions: Select[] = [];
  preprocessors: Preprocessor[] = [];
  columns: string[] = ['Column 1', 'Column 2', 'Column 3']; //TODO: Get column data from backend, when backend is ready

  constructor(private fb: FormBuilder) {}

  addPreprocessor(): void {
    const preprocessorForm = this.fb.nonNullable.group({
      functionID: ['', Validators.required],
      parameters: this.fb.nonNullable.group({})
    });
    this.preprocessors.push({ formGroup: preprocessorForm });
  }

  handleFunctionChange(event: MatSelectChange, index: number): void {
    this.preprocessors[index].formGroup.controls['parameters'] = this.fb.nonNullable.group({});
    this.preprocessors[index].function = undefined;

    const selectedFunction = this.functions.find((_) => _.function === event.value) || null;
    if (selectedFunction) {
      selectedFunction.parameters.forEach((parameter) => {
        const newControl = new FormControl(parameter.default || null);
        if (parameter.required) {
          newControl.setValidators(Validators.required);
        }
        (this.preprocessors[index].formGroup.controls['parameters'] as FormGroup).addControl(parameter.name, newControl);
      });
      this.preprocessors[index].function = selectedFunction;
    }
  }

  reset(): void {
    this.preprocessors = [];
  }

  valid(): boolean {
    for (const preprocessor of this.preprocessors) {
      if (preprocessor.formGroup.invalid) {
        return false;
      }
      if (preprocessor.formGroup.controls['parameters'].invalid) {
        return false;
      }
    }
    return true;
  }
}
