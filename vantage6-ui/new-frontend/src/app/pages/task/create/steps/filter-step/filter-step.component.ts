import { Component, Input } from '@angular/core';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { MatSelectChange } from '@angular/material/select';
import { floatRegex, integerRegex } from 'src/app/helpers/regex.helper';
import { Filter, FilterParameterType } from 'src/app/models/api/algorithm.model';
import { format, parse } from 'date-fns';

@Component({
  selector: 'app-filter-step',
  templateUrl: './filter-step.component.html',
  styleUrls: ['./filter-step.component.scss']
})
export class FilterStepComponent {
  filterParameterType = FilterParameterType;

  @Input() form!: FormArray;
  @Input() filters: Filter[] = [];
  selectedFilters: Array<Filter | null> = [];
  columns: string[] = ['Column 1', 'Column 2', 'Column 3']; //TODO: Get column data from backend, when backend is ready

  constructor(private fb: FormBuilder) {}

  get formGroups(): FormGroup[] {
    //Helps getting typed form groups in template
    return this.form.controls as FormGroup[];
  }

  getSelectedFilter(index: number): Filter | null {
    return this.selectedFilters.length >= index ? this.selectedFilters[index] : null;
  }

  handleFilterChange(event: MatSelectChange, index: number): void {
    const formGroup = this.form.controls[index] as FormGroup;

    const controlsToRemove = Object.keys(formGroup.controls).filter((_) => _ !== 'filterID');
    controlsToRemove.forEach((control) => {
      formGroup.removeControl(control);
    });

    const selectedFunction = this.filters.find((_) => _.function === event.value) || null;
    if (selectedFunction) {
      selectedFunction.parameters.forEach((parameter) => {
        const newControl = new FormControl<any>(null);

        //Set default value
        if (parameter.default) {
          if (parameter.type === FilterParameterType.Date) {
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
        if (parameter.type === FilterParameterType.Integer) {
          newControl.addValidators(Validators.pattern(integerRegex));
        } else if (parameter.type === FilterParameterType.Float) {
          newControl.addValidators(Validators.pattern(floatRegex));
        }
        formGroup.addControl(parameter.name, newControl);
      });
    }
    this.selectedFilters[index] = selectedFunction;
  }

  deleteFilter(index: number): void {
    this.form.removeAt(index);
    this.selectedFilters.splice(index, 1);
  }

  addFilter(): void {
    const filterForm = this.fb.nonNullable.group({
      filterID: ['', Validators.required]
    });
    this.form.push(filterForm);
  }
}
