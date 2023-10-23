import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, FormGroupDirective, Validators } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { Select, SelectParameterType } from 'src/app/models/api/algorithm.model';

@Component({
  selector: 'app-preprocessing-step',
  templateUrl: './preprocessing-step.component.html',
  styleUrls: ['./preprocessing-step.component.scss']
})
export class PreprocessingStepComponent implements OnInit, OnDestroy {
  destroy$ = new Subject();
  selectParameterType = SelectParameterType;

  @Input() functions: Select[] = [];
  form!: FormGroup;
  selectedFunction: Select | null = null;

  columns: string[] = ['Column 1', 'Column 2', 'Column 3']; //TODO: Get column data from backend, when backend is ready

  constructor(
    private fb: FormBuilder,
    private formGroup: FormGroupDirective
  ) {}

  async ngOnInit(): Promise<void> {
    this.form = this.formGroup.control;
    this.form.controls['functionID'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (functionID) => {
      this.handleFunctionChange(functionID);
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  private handleFunctionChange(functionID: string): void {
    this.form.controls['parameters'] = this.fb.nonNullable.group({}); //Reset parameters form group

    this.selectedFunction = this.functions.find((_) => _.function === functionID) || null;
    if (this.selectedFunction) {
      this.selectedFunction.parameters.forEach((parameter) => {
        const newControl = new FormControl(parameter.default || null);
        if (parameter.required) {
          newControl.setValidators(Validators.required);
        }
        (this.form.controls['parameters'] as FormGroup).addControl(parameter.name, newControl);
      });
    }
  }
}
