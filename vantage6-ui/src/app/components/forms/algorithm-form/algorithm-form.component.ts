import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { AlgorithmForm, FunctionType, PartitioningType } from 'src/app/models/api/algorithm.model';

@Component({
  selector: 'app-algorithm-form',
  templateUrl: './algorithm-form.component.html',
  styleUrl: './algorithm-form.component.scss'
})
export class AlgorithmFormComponent implements OnInit {
  @Input() algorithm?: Algorithm;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<AlgorithmForm> = new EventEmitter();

  isEdit: boolean = false;
  isLoading: boolean = true;
  partitionTypes = Object.values(PartitioningType);
  functionTypes = Object.values(FunctionType);

  databaseForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: ['']
  });
  argumentForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    type: ['', [Validators.required]]
  });
  functionForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    type: ['', [Validators.required]],
    arguments: this.fb.nonNullable.array([this.argumentForm]),
    databases: this.fb.nonNullable.array([this.databaseForm])
  });
  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    image: ['', [Validators.required]],
    partitioning: ['', [Validators.required]],
    vantage6_version: ['', [Validators.required]],
    functions: this.fb.nonNullable.array([this.functionForm])
  });

  constructor(private fb: FormBuilder) {}

  async ngOnInit(): Promise<void> {
    this.isEdit = !!this.algorithm;
    if (this.algorithm) {
      // this.form.controls.name.setValue(this.collaboration.name);
      // this.form.controls.encrypted.setValue(this.collaboration.encrypted);
      // this.form.controls.organizations.setValue(this.collaboration.organizations);
    }
    this.isLoading = false;
  }

  handleSubmit() {
    console.log(this.form);
    // if (this.form.valid) {
    //   this.submitted.emit(this.form.getRawValue());
    // }
  }

  handleCancel() {
    this.cancelled.emit();
  }

  addFunction(): void {
    this.form.controls.functions.push(this.functionForm);
  }

  deleteFunction(index: number): void {
    this.form.controls.functions.removeAt(index);
  }

  addParameter(functionFormGroup: FormGroup): void {
    (functionFormGroup.controls['arguments'] as FormArray).push(this.argumentForm);
    console.log(functionFormGroup);
  }

  addDatabase(functionFormGroup: FormGroup): void {
    (functionFormGroup.controls['databases'] as FormArray).push(this.databaseForm);
  }

  get functionFormGroups(): FormGroup[] {
    return this.form.controls.functions.controls as FormGroup[];
  }
}
