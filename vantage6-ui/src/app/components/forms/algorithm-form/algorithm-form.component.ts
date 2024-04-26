import { Component, EventEmitter, Input, OnInit, Output, QueryList, ViewChildren } from '@angular/core';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatExpansionPanel } from '@angular/material/expansion';
import { AlgorithmForm, ArgumentType, FunctionType, PartitioningType } from 'src/app/models/api/algorithm.model';

@Component({
  selector: 'app-algorithm-form',
  templateUrl: './algorithm-form.component.html',
  styleUrl: './algorithm-form.component.scss'
})
export class AlgorithmFormComponent implements OnInit {
  @Input() algorithm?: Algorithm;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<AlgorithmForm> = new EventEmitter();
  @ViewChildren('expansionPanel') matExpansionPanels?: QueryList<MatExpansionPanel>;

  isEdit: boolean = false;
  isLoading: boolean = true;
  partitionTypes = Object.values(PartitioningType);
  functionTypes = Object.values(FunctionType);
  paramTypes = Object.values(ArgumentType);

  // FIXME these forms are also defined in a separate function at the end but we need
  // to define them here to prevent type errors in the form... find a solution to define
  // only once
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
    // Note that we initialize the functions form to already contain one function
    functions: this.fb.nonNullable.array([this.functionForm])
  });

  constructor(private fb: FormBuilder) {}

  async ngOnInit(): Promise<void> {
    this.isEdit = !!this.algorithm;
    if (this.algorithm) {
      // this.form.controls.name.setValue(this.collaboration.name);
      // this.form.controls.encrypted.setValue(this.collaboration.encrypted);
      // this.form.controls.organizations.setValue(this.collaboration.organizations);
    } else {
      this.initializeFormForCreate();
    }
    this.isLoading = false;
  }

  handleSubmit() {
    if (this.form.valid) {
      this.submitted.emit(this.form.getRawValue());
    }
  }

  handleCancel() {
    this.cancelled.emit();
  }

  addFunction(): void {
    // close expansion panels of existing functions, then add a new function
    this.closeFunctionExpansionPanels();
    this.form.controls.functions.push(this.getFunctionForm());
  }

  deleteFunction(index: number): void {
    this.form.controls.functions.removeAt(index);
  }

  addParameter(functionFormGroup: FormGroup): void {
    (functionFormGroup.controls['arguments'] as FormArray).push(this.getArgumentForm());
  }

  deleteParameter(functionFormGroup: FormGroup, index: number): void {
    (functionFormGroup.controls['arguments'] as FormArray).removeAt(index);
  }

  addDatabase(functionFormGroup: FormGroup): void {
    (functionFormGroup.controls['databases'] as FormArray).push(this.getDatabaseForm());
  }

  deleteDatabase(functionFormGroup: FormGroup, index: number): void {
    (functionFormGroup.controls['databases'] as FormArray).removeAt(index);
  }

  get functionFormGroups(): FormGroup[] {
    return this.form.controls.functions.controls as FormGroup[];
  }

  getParamFormGroups(functionIndex: number): FormGroup[] {
    return this.form.controls.functions.controls[functionIndex].controls.arguments.controls as FormGroup[];
  }

  getDatabaseFormGroups(functionIndex: number): FormGroup[] {
    return this.form.controls.functions.controls[functionIndex].controls.databases.controls as FormGroup[];
  }

  private initializeFormForCreate(): void {
    // on initialization, ensure there is one function which contains no arguments
    // and no databases
    this.form.controls.functions.clear();
    this.addFunction();
    this.form.controls.functions.controls[0].controls.arguments.clear();
    this.form.controls.functions.controls[0].controls.databases.clear();
  }

  private closeFunctionExpansionPanels(): void {
    if (this.matExpansionPanels) {
      this.matExpansionPanels.forEach((panel) => panel.close());
    }
  }

  private getFunctionForm(): FormGroup {
    return this.fb.group({
      name: ['', [Validators.required]],
      description: [''],
      type: ['', [Validators.required]],
      arguments: this.fb.array([]),
      databases: this.fb.array([])
    });
  }

  private getArgumentForm(): FormGroup {
    return this.fb.group({
      name: ['', [Validators.required]],
      description: [''],
      type: ['', [Validators.required]]
    });
  }

  private getDatabaseForm(): FormGroup {
    return this.fb.group({
      name: ['', [Validators.required]],
      description: ['']
    });
  }
}
