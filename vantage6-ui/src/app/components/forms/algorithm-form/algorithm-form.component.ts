import { AfterViewInit, ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output, QueryList, ViewChildren } from '@angular/core';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatExpansionPanel } from '@angular/material/expansion';
import { readFile } from 'src/app/helpers/file.helper';
import { AlgorithmForm, ArgumentType, FunctionForm, FunctionType, PartitioningType } from 'src/app/models/api/algorithm.model';
import { VisualizationType, getVisualizationSchema } from 'src/app/models/api/visualization.model';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'app-algorithm-form',
  templateUrl: './algorithm-form.component.html',
  styleUrl: './algorithm-form.component.scss'
})
export class AlgorithmFormComponent implements OnInit, AfterViewInit {
  @Input() algorithm?: AlgorithmForm;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  // Note: we are using any because the form is dynamic and the structure is not known
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  @Output() submitted: EventEmitter<any> = new EventEmitter();
  @ViewChildren('expansionPanel') matExpansionPanels?: QueryList<MatExpansionPanel>;

  isEdit: boolean = false;
  isLoading: boolean = true;
  partitionTypes = Object.values(PartitioningType);
  functionTypes = Object.values(FunctionType);
  paramTypes = Object.values(ArgumentType);
  visualizationTypes = Object.values(VisualizationType);
  selectedFile: File | null = null;
  uploadForm = this.fb.nonNullable.group({
    jsonFile: ''
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  schemaDetails: { [id: string]: any } = {};

  // FIXME these forms are also defined in a separate function at the end but we need
  // to define them here to prevent type errors in the form... find a solution to define
  // only once
  databaseForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: ['']
  });
  argumentForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    display_name: [''],
    description: [''],
    type: ['', [Validators.required]]
  });
  visualizationSchemaForm = this.fb.nonNullable.group({});
  visualizationForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    type: ['', [Validators.required]],
    schema: this.visualizationSchemaForm
  });
  functionForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    display_name: [''],
    description: [''],
    type: ['', [Validators.required]],
    arguments: this.fb.nonNullable.array([this.argumentForm]),
    databases: this.fb.nonNullable.array([this.databaseForm]),
    ui_visualizations: this.fb.nonNullable.array([this.visualizationForm])
  });
  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    image: ['', [Validators.required]],
    partitioning: ['', [Validators.required]],
    vantage6_version: ['', [Validators.required]],
    code_url: ['', [Validators.required]],
    documentation_url: [''],
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
      const formValue = this.visualizationSchemasToArrays(this.form.getRawValue());
      this.submitted.emit(formValue);
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

  addVisualization(functionFormGroup: FormGroup): void {
    (functionFormGroup.controls['ui_visualizations'] as FormArray).push(this.getVisualizationForm());
  }

  deleteVisualization(functionFormGroup: FormGroup, index: number): void {
    (functionFormGroup.controls['ui_visualizations'] as FormArray).removeAt(index);
  }

  get functionFormGroups(): FormGroup[] {
    return this.form.controls.functions.controls as FormGroup[];
  }

  getVisSchemaForm(funcIdx: number, visIdx: number): FormGroup {
    return <FormGroup>this.form.controls.functions.controls[funcIdx].controls.ui_visualizations.controls[visIdx].controls.schema;
  }

  setVisSchema(funcIdx: number, visIdx: number, visType: VisualizationType) {
    const visSchemaForm = <FormGroup>(
      this.form.controls.functions.controls[funcIdx].controls.ui_visualizations.controls[visIdx].controls.schema
    );

    this.setSchemaControls(visSchemaForm, visType, funcIdx, visIdx);
  }

  getVisSchemaField(funcIdx: number, visIdx: number, schemaField: string, infoField: string): string {
    return this.schemaDetails[`${funcIdx}-${visIdx}`][schemaField][infoField];
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
    this.form.controls.code_url.setValue(this.algorithm.code_url);
    this.form.controls.documentation_url.setValue(this.algorithm.documentation_url || '');
    this.form.controls.functions.clear();
    this.algorithm.functions.forEach((func, funcIdx) => {
      const functionFormGroup = this.getFunctionForm();
      functionFormGroup.controls['name'].setValue(func.name);
      functionFormGroup.controls['display_name'].setValue(func.display_name);
      functionFormGroup.controls['description'].setValue(func.description);
      functionFormGroup.controls['type'].setValue(func.type);
      if (func.arguments) {
        func.arguments.forEach((arg) => {
          const argumentFormGroup = this.getArgumentForm();
          argumentFormGroup.controls['name'].setValue(arg.name);
          argumentFormGroup.controls['display_name'].setValue(arg.display_name);
          argumentFormGroup.controls['description'].setValue(arg.description);
          argumentFormGroup.controls['type'].setValue(arg.type);
          (functionFormGroup.controls['arguments'] as FormArray).push(argumentFormGroup);
        });
      }
      if (func.databases) {
        func.databases.forEach((db) => {
          const databaseFormGroup = this.getDatabaseForm();
          databaseFormGroup.controls['name'].setValue(db.name);
          databaseFormGroup.controls['description'].setValue(db.description);
          (functionFormGroup.controls['databases'] as FormArray).push(databaseFormGroup);
        });
      }
      if (func.ui_visualizations) {
        func.ui_visualizations.forEach((vis, visIdx) => {
          const visualizationFormGroup = this.getVisualizationForm();
          visualizationFormGroup.controls['name'].setValue(vis.name);
          visualizationFormGroup.controls['description'].setValue(vis.description);
          visualizationFormGroup.controls['type'].setValue(vis.type);
          const visSchemaForm = <FormGroup>visualizationFormGroup.controls['schema'];
          // add controls for all fields of the schema
          this.setSchemaControls(visSchemaForm, vis.type, funcIdx, visIdx);
          // set the values of the schema that were already defined before
          if (vis.schema) {
            Object.keys(vis.schema).forEach((key) => {
              visSchemaForm.controls[key].setValue(vis.schema[key]);
            });
          }
          (functionFormGroup.controls['ui_visualizations'] as FormArray).push(visualizationFormGroup);
        });
      }
      (this.form.controls.functions as FormArray).push(functionFormGroup);
    });
  }

  private setSchemaControls(visSchemaForm: FormGroup, visType: VisualizationType, funcIdx: number, visIdx: number) {
    // remove old controls
    Object.keys(visSchemaForm.controls).forEach((key) => {
      visSchemaForm.removeControl(key);
    });
    // add controls for all fields of the schema
    const schema = getVisualizationSchema(visType);
    Object.keys(schema).forEach((key) => {
      const details = schema[key];
      const validators = details.required ? [Validators.required] : [];
      if (details.type === 'array') {
        visSchemaForm.addControl(key, this.fb.control([], validators));
      } else {
        visSchemaForm.addControl(key, this.fb.control('', validators));
      }
    });
    // save which schema is used for this visualization index
    this.schemaDetails[`${funcIdx}-${visIdx}`] = schema;
  }

  private initializeFormForCreate(): void {
    // on initialization, ensure there is one function which contains no arguments
    // and no databases
    this.form.controls.functions.clear();
    this.addFunction();
    this.form.controls.functions.controls[0].controls.arguments.clear();
    this.form.controls.functions.controls[0].controls.databases.clear();
    this.form.controls.functions.controls[0].controls.ui_visualizations.clear();
  }

  // visualization schemas should sometimes contain arrays, while input may be comma-separated strings. Convert those
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private visualizationSchemasToArrays(formValue: any): any {
    // TODO it would be better to already have arrays in the input -- JSON validation there? Or multiple fields (as in task parameters)?
    formValue.functions.forEach((func: FunctionForm) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      func.ui_visualizations.forEach((vis: any) => {
        const schema = vis.schema;
        const schemaRequirements = getVisualizationSchema(vis.type);
        Object.keys(schema).forEach((parameter) => {
          const parameterRequirements = schemaRequirements[parameter];
          if (typeof schema[parameter] === 'string' && parameterRequirements.type === 'array') {
            // convert comma separated strings to arrays and remove empty strings
            schema[parameter] = schema[parameter]
              .split(',')
              .map((s: string) => s.trim())
              .filter((s: string) => s !== '');
          } else if (parameterRequirements.type === 'number') {
            if (schema[parameter] !== '') schema[parameter] = Number(schema[parameter]);
            else delete schema[parameter];
          }
        });
      });
    });
    return formValue;
  }

  private closeFunctionExpansionPanels(): void {
    if (this.matExpansionPanels) {
      this.matExpansionPanels.forEach((panel) => panel.close());
    }
  }

  private getFunctionForm(): FormGroup {
    return this.fb.group({
      name: ['', [Validators.required]],
      display_name: [''],
      description: [''],
      type: ['', [Validators.required]],
      arguments: this.fb.array([]),
      databases: this.fb.array([]),
      ui_visualizations: this.fb.array([])
    });
  }

  private getArgumentForm(): FormGroup {
    return this.fb.group({
      name: ['', [Validators.required]],
      display_name: [''],
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

  private getVisualizationForm(): FormGroup {
    return this.fb.group({
      name: ['', [Validators.required]],
      description: [''],
      type: ['', [Validators.required]],
      schema: this.fb.nonNullable.group({})
    });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
