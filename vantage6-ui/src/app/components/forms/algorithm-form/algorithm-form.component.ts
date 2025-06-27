import { AfterViewInit, ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output, QueryList, ViewChildren } from '@angular/core';
import {
  AbstractControl,
  FormArray,
  FormBuilder,
  FormGroup,
  ValidationErrors,
  Validators,
  ReactiveFormsModule,
  FormControl
} from '@angular/forms';
import {
  MatExpansionPanel,
  MatAccordion,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
  MatExpansionPanelContent
} from '@angular/material/expansion';
import { readFile } from 'src/app/helpers/file.helper';
import {
  AlgorithmForm,
  ArgumentForm,
  ArgumentType,
  ConditionalArgComparatorType,
  FunctionForm,
  PartitioningType
} from 'src/app/models/api/algorithm.model';
import { VisualizationType, getVisualizationSchema } from 'src/app/models/api/visualization.model';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { isTruthy } from 'src/app/helpers/utils.helper';
import { isArgumentWithAllowedValues, isListTypeArgument } from 'src/app/helpers/algorithm.helper';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { MatFormField, MatLabel, MatSuffix } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatButton } from '@angular/material/button';
import { NgIf, NgFor, TitleCasePipe, KeyValuePipe } from '@angular/common';
import { MatSelect } from '@angular/material/select';
import { MatOption } from '@angular/material/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatTooltip } from '@angular/material/tooltip';
import { MatRadioGroup, MatRadioButton } from '@angular/material/radio';
import { AlertComponent } from '../../alerts/alert/alert.component';
import { NumberOnlyDirective } from '../../../directives/numberOnly.directive';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { AlgorithmStepType } from 'src/app/models/api/session.models';
import { MatChipFormComponent } from '../mat-chip-form/mat-chip-form.component';

@Component({
  selector: 'app-algorithm-form',
  templateUrl: './algorithm-form.component.html',
  styleUrl: './algorithm-form.component.scss',
  imports: [
    MatCard,
    MatCardHeader,
    MatCardTitle,
    MatCardContent,
    ReactiveFormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatButton,
    MatSuffix,
    NgIf,
    MatSelect,
    NgFor,
    MatOption,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatExpansionPanelContent,
    MatCheckbox,
    MatTooltip,
    MatRadioGroup,
    MatRadioButton,
    AlertComponent,
    NumberOnlyDirective,
    MatProgressSpinner,
    TitleCasePipe,
    KeyValuePipe,
    TranslateModule,
    MatChipFormComponent
  ]
})
export class AlgorithmFormComponent implements OnInit, AfterViewInit {
  @Input() algorithm?: AlgorithmForm;
  @Output() cancelled: EventEmitter<void> = new EventEmitter();
  // Note: we are using any because the form is dynamic and the structure is not known
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  @Output() submitted: EventEmitter<any> = new EventEmitter();
  @ViewChildren('expansionPanel') matExpansionPanels?: QueryList<MatExpansionPanel>;
  argumentType = ArgumentType;
  isTruthy = isTruthy;
  isListTypeArgument = isListTypeArgument;
  isArgumentWithAllowedValues = isArgumentWithAllowedValues;

  isEdit: boolean = false;
  isLoading: boolean = true;
  partitionTypes = Object.values(PartitioningType);
  functionStepTypes = Object.values(AlgorithmStepType);
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
  argumentForm = this.fb.nonNullable.group(
    {
      name: ['', [Validators.required]],
      display_name: [''],
      description: [''],
      type: ['', [Validators.required]],
      has_default_value: [false],
      is_default_value_null: [false],
      default_value: [''],
      hasCondition: [false],
      conditional_on: [''],
      conditional_operator: [''],
      conditional_value: [''],
      conditionalValueNull: [false],
      is_frontend_only: [false],
      allowed_values: [[]]
    },
    { validators: this.conditionalFieldsValidator.bind(this) }
  );
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
    step_type: ['', [Validators.required]],
    hidden: [false],
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
    submission_comments: [''],
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
      const formValue = this.formatFormForSubmission(this.form.getRawValue());
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

  getAvailableConditionalArguments(functionFormGroup: FormGroup, argumentIndex: number): string[] {
    // return the names of other arguments than the current argument, and only those of types
    // that are suitable as conditional argument. E.g. it is not currently implemented to
    // have a condition if a list of floats is exactly (0.5, 0.7) as that is an unlikely usecase
    const currentArgumentName = (functionFormGroup.controls['arguments'] as FormArray).controls[argumentIndex].value.name;
    return (functionFormGroup.controls['arguments'] as FormArray).controls
      .map((control) => control.value)
      .filter((arg) =>
        [ArgumentType.Boolean, ArgumentType.Integer, ArgumentType.Float, ArgumentType.Column, ArgumentType.String].includes(arg.type)
      )
      .map((arg) => arg.name)
      .filter((name) => name !== currentArgumentName);
  }

  getAvailableComparators(functionFormGroup: FormGroup, parameterFormGroup: FormGroup): string[] {
    const condArgType = this.getConditionalParamType(functionFormGroup, parameterFormGroup);
    if (condArgType === ArgumentType.Integer || condArgType === ArgumentType.Float) {
      return Object.values(ConditionalArgComparatorType);
    } else {
      return [ConditionalArgComparatorType.Equal, ConditionalArgComparatorType.NotEqual];
    }
  }

  getConditionalParamInputType(functionFormGroup: FormGroup, parameterFormGroup: FormGroup): string {
    const condArgType = this.getConditionalParamType(functionFormGroup, parameterFormGroup);
    if (condArgType === ArgumentType.Integer || condArgType === ArgumentType.Float) {
      return 'number';
    } else {
      return 'text';
    }
  }

  isConditionalArgBoolean(functionFormGroup: FormGroup, parameterFormGroup: FormGroup): boolean {
    const condArgType = this.getConditionalParamType(functionFormGroup, parameterFormGroup);
    return condArgType === ArgumentType.Boolean;
  }

  private getConditionalParamType(functionFormGroup: FormGroup, parameterFormGroup: FormGroup): ArgumentType {
    const conditionalArgName = parameterFormGroup.controls['conditional_on'].value;
    return (functionFormGroup.controls['arguments'] as FormArray).controls.find((control) => control.value.name === conditionalArgName)
      ?.value.type;
  }

  hasDefaultValueChanges(hasDefaultValue: boolean, defaultValueControl: FormControl<string>): void {
    if (!hasDefaultValue) {
      defaultValueControl.setValue('');
    }
  }

  hasAllowedValues(type: string, allowedValues: string[] | undefined): boolean {
    return this.isArgumentWithAllowedValues(type) && allowedValues !== undefined && allowedValues.length > 0;
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
    this.form.controls.submission_comments.setValue(this.algorithm.submission_comments || '');
    this.form.controls.functions.clear();
    this.algorithm.functions.forEach((func, funcIdx) => {
      const functionFormGroup = this.getFunctionForm();
      functionFormGroup.controls['name'].setValue(func.name);
      functionFormGroup.controls['display_name'].setValue(func.display_name);
      functionFormGroup.controls['description'].setValue(func.description);
      functionFormGroup.controls['step_type'].setValue(func.step_type);
      functionFormGroup.controls['standalone'].setValue(func.standalone);
      if (func.arguments) {
        func.arguments.forEach((arg) => {
          const argumentFormGroup = this.getArgumentForm();
          argumentFormGroup.controls['name'].setValue(arg.name);
          argumentFormGroup.controls['display_name'].setValue(arg.display_name);
          argumentFormGroup.controls['description'].setValue(arg.description);
          argumentFormGroup.controls['type'].setValue(arg.type);
          argumentFormGroup.controls['allowed_values'].setValue(arg.allowed_values);
          argumentFormGroup.controls['is_frontend_only'].setValue(arg.is_frontend_only);
          argumentFormGroup.controls['has_default_value'].setValue(arg.has_default_value);
          argumentFormGroup.controls['is_default_value_null'].setValue(arg.default_value === null);
          if (arg.default_value != null) {
            if (
              arg.type === ArgumentType.StringList ||
              arg.type === ArgumentType.ColumnList ||
              arg.type === ArgumentType.ColumnList ||
              arg.type === ArgumentType.FloatList ||
              arg.type === ArgumentType.IntegerList
            ) {
              try {
                const array_vals = JSON.parse(arg.default_value as string);
                argumentFormGroup.controls['default_value'].setValue(array_vals.join(','));
              } catch {
                argumentFormGroup.controls['default_value'].setValue(arg.default_value);
              }
            } else if (arg.type === ArgumentType.Boolean) {
              if (isTruthy(arg.default_value) || arg.default_value == '0') {
                argumentFormGroup.controls['default_value'].setValue(true);
              } else {
                argumentFormGroup.controls['default_value'].setValue(false);
              }
            } else {
              argumentFormGroup.controls['default_value'].setValue(arg.default_value);
            }
          }
          argumentFormGroup.controls['hasCondition'].setValue(arg.conditional_on !== undefined);
          argumentFormGroup.controls['conditional_on'].setValue(arg.conditional_on);
          argumentFormGroup.controls['conditional_operator'].setValue(arg.conditional_operator);
          if (arg.conditional_on) {
            const conditionalArg = func.arguments.find((other_arg: ArgumentForm) => other_arg.name === arg.conditional_on);
            if (conditionalArg?.type === ArgumentType.Boolean) {
              argumentFormGroup.controls['conditionalValueNull'].setValue(false);
              argumentFormGroup.controls['conditional_value'].setValue(isTruthy(arg.conditional_value));
            } else {
              argumentFormGroup.controls['conditionalValueNull'].setValue(arg.conditional_value === null);
              argumentFormGroup.controls['conditional_value'].setValue(arg.conditional_value);
            }
          }
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

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private formatFormForSubmission(formValue: any): any {
    // TODO it would be better to already have arrays in the input -- JSON validation there? Or multiple fields (as in task parameters)?
    formValue.functions.forEach((func: FunctionForm) => {
      // visualization schemas should sometimes contain arrays, while input may be comma-separated strings. Convert those
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
      // convert default values to strings, as they are always stored as strings in the database
      func.arguments.forEach((arg) => {
        if (arg.default_value != null) {
          arg.default_value = arg.default_value.toString();
        }
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
      step_type: ['', [Validators.required]],
      standalone: [true],
      arguments: this.fb.array([]),
      databases: this.fb.array([]),
      ui_visualizations: this.fb.array([])
    });
  }

  private getArgumentForm(): FormGroup {
    return this.fb.group(
      {
        name: ['', [Validators.required]],
        display_name: [''],
        description: [''],
        type: ['', [Validators.required]],
        has_default_value: [false],
        is_default_value_null: [false],
        default_value: [''],
        hasCondition: [false],
        conditional_on: [''],
        conditional_operator: [''],
        conditional_value: [''],
        conditionalValueNull: [false],
        is_frontend_only: [false],
        allowed_values: [[]]
      },
      { validators: this.conditionalFieldsValidator.bind(this) }
    );
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

  conditionalFieldsValidator(control: AbstractControl): ValidationErrors | null {
    const conditionalOn = control.get('conditional_on')?.value;
    const conditionalOperator = control.get('conditional_operator')?.value;
    const conditionalValue = control.get('conditional_value')?.value;
    const conditionalValueNull = control.get('conditionalValueNull')?.value;

    // note that the check whether conditionalValue is set, is different from check whether the
    // other fields are set. This is because the conditionalValue may be set to 'false'.
    const isConditionalValueSet =
      conditionalValueNull || (conditionalValue !== null && conditionalValue !== undefined && conditionalValue !== '');

    const allFieldsFilled = conditionalOn && conditionalOperator && isConditionalValueSet;
    const allFieldsEmpty = !conditionalOn && !conditionalOperator && !isConditionalValueSet;

    if (allFieldsFilled || allFieldsEmpty) {
      return null; // Valid
    } else {
      return { conditionalFields: this.translateService.instant('algorithm-create.function.parameter.conditional-fields-error') }; // Invalid
    }
  }
}
