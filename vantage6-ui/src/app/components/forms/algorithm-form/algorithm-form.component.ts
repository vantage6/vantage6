import { AfterViewInit, ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output, QueryList, ViewChildren } from '@angular/core';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatExpansionPanel } from '@angular/material/expansion';
import { readFile } from 'src/app/helpers/file.helper';
import { Algorithm, AlgorithmForm, ArgumentType, FunctionType, PartitioningType } from 'src/app/models/api/algorithm.model';
import { MessageDialogComponent } from '../../dialogs/message-dialog/message-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'app-algorithm-form',
  templateUrl: './algorithm-form.component.html',
  styleUrl: './algorithm-form.component.scss'
})
export class AlgorithmFormComponent implements OnInit, AfterViewInit {
  @Input() algorithm?: Algorithm | AlgorithmForm;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  @Output() submitted: EventEmitter<AlgorithmForm> = new EventEmitter();
  @ViewChildren('expansionPanel') matExpansionPanels?: QueryList<MatExpansionPanel>;

  isEdit: boolean = false;
  isLoading: boolean = true;
  partitionTypes = Object.values(PartitioningType);
  functionTypes = Object.values(FunctionType);
  paramTypes = Object.values(ArgumentType);
  selectedFile: File | null = null;
  uploadForm = this.fb.nonNullable.group({
    jsonFile: ''
  });

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

  constructor(
    private fb: FormBuilder,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private changeDetectorRef: ChangeDetectorRef
  ) {}

  async ngOnInit(): Promise<void> {
    this.isEdit = !!this.algorithm;
    if (this.algorithm) {
      this.initializeFormFromAlgorithm();
    } else {
      this.initializeFormForCreate();
    }
    this.isLoading = false;
  }

  ngAfterViewInit(): void {
    // if editing algorithm, close the expansion panels to prevent information overload
    if (this.isEdit) {
      this.closeFunctionExpansionPanels();
    }
    this.changeDetectorRef.detectChanges();
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

  async selectedJsonFile(event: Event) {
    this.selectedFile = (event.target as HTMLInputElement).files?.item(0) || null;

    if (!this.selectedFile) return;
    const fileData = await readFile(this.selectedFile);

    this.uploadForm.controls.jsonFile.setValue(fileData || '');
    try {
      const algorithmForm: AlgorithmForm = JSON.parse(this.uploadForm.controls.jsonFile.value);
      this.algorithm = algorithmForm;
      this.initializeFormFromAlgorithm();
      // to prevent visual overload, attempt to close the expansion panels
      // TODO hacky solution - better not to rely on timeout. For edit it is done via
      // ngAfterViewInit, but for upload it is not possible to do it there - find out how
      setTimeout(() => {
        this.closeFunctionExpansionPanels();
      }, 500);
    } catch (error) {
      this.showJsonUploadError(error);
    }
  }

  private initializeFormFromAlgorithm(): void {
    if (!this.algorithm) return;
    // initialize the form with the values of the algorithm
    this.form.controls.name.setValue(this.algorithm.name);
    this.form.controls.description.setValue(this.algorithm?.description || '');
    this.form.controls.image.setValue(this.algorithm.image);
    this.form.controls.partitioning.setValue(this.algorithm.partitioning);
    this.form.controls.vantage6_version.setValue(this.algorithm.vantage6_version);
    this.form.controls.functions.clear();
    this.algorithm.functions.forEach((func) => {
      const functionFormGroup = this.getFunctionForm();
      functionFormGroup.controls['name'].setValue(func.name);
      functionFormGroup.controls['description'].setValue(func.description);
      functionFormGroup.controls['type'].setValue(func.type);
      func.arguments.forEach((arg) => {
        const argumentFormGroup = this.getArgumentForm();
        argumentFormGroup.controls['name'].setValue(arg.name);
        argumentFormGroup.controls['description'].setValue(arg.description);
        argumentFormGroup.controls['type'].setValue(arg.type);
        (functionFormGroup.controls['arguments'] as FormArray).push(argumentFormGroup);
      });
      func.databases.forEach((db) => {
        const databaseFormGroup = this.getDatabaseForm();
        databaseFormGroup.controls['name'].setValue(db.name);
        databaseFormGroup.controls['description'].setValue(db.description);
        (functionFormGroup.controls['databases'] as FormArray).push(databaseFormGroup);
      });
      (this.form.controls.functions as FormArray).push(functionFormGroup);
    });
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

  private showJsonUploadError(error: any): void {
    this.dialog.open(MessageDialogComponent, {
      data: {
        title: this.translateService.instant('algorithm-create.card-from-json.error-title'),
        content: [error.message],
        confirmButtonText: this.translateService.instant('general.close'),
        confirmButtonType: 'default'
      }
    });
  }
}
