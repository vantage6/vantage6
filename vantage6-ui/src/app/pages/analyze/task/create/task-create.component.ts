import { AfterViewInit, ChangeDetectorRef, Component, HostBinding, OnDestroy, OnInit, ViewChild, ViewEncapsulation } from '@angular/core';
import { AbstractControl, FormArray, FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import {
  Algorithm,
  ArgumentType,
  AlgorithmFunction,
  Argument,
  FunctionType,
  AlgorithmFunctionExtended,
  ConditionalArgComparatorType
} from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { BaseNode, NodeStatus } from 'src/app/models/api/node.model';
import { ColumnRetrievalInput, CreateTask, CreateTaskInput, Task, TaskDatabase } from 'src/app/models/api/task.models';
import { TaskService } from 'src/app/services/task.service';
import { routePaths } from 'src/app/routes';
import { Router } from '@angular/router';
import { PreprocessingStepComponent } from './steps/preprocessing-step/preprocessing-step.component';
import {
  addParameterFormControlsForFunction,
  getTaskDatabaseFromForm,
  getDatabaseTypesFromForm
} from 'src/app/pages/analyze/task/task.helper';
import { readFile } from 'src/app/helpers/file.helper';
import { DatabaseStepComponent } from './steps/database-step/database-step.component';
import { FilterStepComponent } from './steps/filter-step/filter-step.component';
import { NodeService } from 'src/app/services/node.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { MatStepper, MatStepperIcon, MatStep, MatStepLabel, MatStepperNext, MatStepperPrevious } from '@angular/material/stepper';
import { SnackbarService } from 'src/app/services/snackbar.service';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Collaboration } from 'src/app/models/api/collaboration.model';
import { BaseStudy, StudyOrCollab } from 'src/app/models/api/study.model';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { MAX_ATTEMPTS_RENEW_NODE, SECONDS_BETWEEN_ATTEMPTS_RENEW_NODE } from 'src/app/models/constants/wait';
import { floatRegex, integerRegex } from 'src/app/helpers/regex.helper';
import { EncryptionService } from 'src/app/services/encryption.service';
import { environment } from 'src/environments/environment';
import { isTruthy } from 'src/app/helpers/utils.helper';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf, NgFor, NgTemplateOutlet } from '@angular/common';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatFormField, MatLabel, MatSuffix } from '@angular/material/form-field';
import { MatSelect } from '@angular/material/select';
import { MatOption } from '@angular/material/core';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatInput } from '@angular/material/input';
import { AlertComponent } from '../../../../components/alerts/alert/alert.component';
import { NumberOnlyDirective } from '../../../../directives/numberOnly.directive';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { HighlightedTextPipe } from '../../../../pipes/highlighted-text.pipe';

@Component({
    selector: 'app-task-create',
    templateUrl: './task-create.component.html',
    styleUrls: ['./task-create.component.scss'],
    encapsulation: ViewEncapsulation.None,
    imports: [
        PageHeaderComponent,
        NgIf,
        MatCard,
        MatCardContent,
        MatStepper,
        MatStepperIcon,
        MatIcon,
        MatStep,
        ReactiveFormsModule,
        MatStepLabel,
        MatFormField,
        MatLabel,
        MatSelect,
        MatOption,
        NgFor,
        MatButton,
        MatStepperNext,
        MatInput,
        MatIconButton,
        MatSuffix,
        AlertComponent,
        MatStepperPrevious,
        DatabaseStepComponent,
        PreprocessingStepComponent,
        FilterStepComponent,
        NumberOnlyDirective,
        MatCheckbox,
        MatProgressSpinner,
        NgTemplateOutlet,
        TranslateModule,
        HighlightedTextPipe
    ]
})
export class TaskCreateComponent implements OnInit, OnDestroy, AfterViewInit {
  @HostBinding('class') class = 'card-container';

  @ViewChild(PreprocessingStepComponent)
  preprocessingStep?: PreprocessingStepComponent;
  @ViewChild(FilterStepComponent)
  filterStep?: FilterStepComponent;
  @ViewChild(DatabaseStepComponent)
  databaseStepComponent?: DatabaseStepComponent;
  @ViewChild('stepper') private myStepper: MatStepper | null = null;

  destroy$ = new Subject();
  routes = routePaths;
  argumentType = ArgumentType;
  functionType = FunctionType;
  studyOrCollab = StudyOrCollab;

  study: BaseStudy | null = null;
  algorithms: Algorithm[] = [];
  algorithm: Algorithm | null = null;
  collaboration?: Collaboration | null = null;
  organizations: BaseOrganization[] = [];
  functions: AlgorithmFunctionExtended[] = [];
  filteredFunctions: AlgorithmFunctionExtended[] = [];
  function: AlgorithmFunctionExtended | null = null;
  node: BaseNode | null = null;
  columns: string[] = [];
  isLoading: boolean = true;
  isLoadingColumns: boolean = false;
  hasLoadedColumns: boolean = false;
  isSubmitting: boolean = false;
  isTaskRepeat: boolean = false;
  isDataInitialized: boolean = false;
  isNgInitDone: boolean = false;
  repeatedTask: Task | null = null;

  studyForm = this.fb.nonNullable.group({
    studyOrCollabID: ['', Validators.required]
  });
  functionForm = this.fb.nonNullable.group({
    algorithmFunctionSpec: ['', Validators.required],
    algorithmFunctionSearch: '',
    organizationIDs: ['', Validators.required],
    name: ['', Validators.required],
    description: ''
  });
  databaseForm = this.fb.nonNullable.group({});
  preprocessingForm = this.fb.array([]);
  filterForm = this.fb.array([]);
  parameterForm: FormGroup = this.fb.nonNullable.group({});

  private nodeStatusUpdateSubscription?: Subscription;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private changeDetectorRef: ChangeDetectorRef,
    private algorithmService: AlgorithmService,
    private taskService: TaskService,
    private nodeService: NodeService,
    public chosenCollaborationService: ChosenCollaborationService,
    private socketioConnectService: SocketioConnectService,
    private snackBarService: SnackbarService,
    private translateService: TranslateService,
    private organizationService: OrganizationService,
    private encryptionService: EncryptionService
  ) {}

  async ngOnInit(): Promise<void> {
    this.isTaskRepeat = this.router.url.startsWith(routePaths.taskCreateRepeat);

    this.chosenCollaborationService.isInitialized$.pipe(takeUntil(this.destroy$)).subscribe((initialized) => {
      if (initialized && !this.isDataInitialized) {
        this.initData();
      }
    });
  }

  async ngAfterViewInit(): Promise<void> {
    // recursively wait until ngInit is done
    if (!this.isNgInitDone) {
      await new Promise((f) => setTimeout(f, 200));
      this.ngAfterViewInit();
      return;
    }

    // setup repeating task if needed
    if (this.isTaskRepeat) {
      this.isLoading = true;
      const splitted = this.router.url.split('/');
      const taskID = splitted[splitted.length - 1];
      await this.setupRepeatTask(taskID);
      this.isLoading = false;
    }
    this.changeDetectorRef.detectChanges();
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
    this.nodeStatusUpdateSubscription?.unsubscribe();
  }

  get shouldShowStudyStep(): boolean {
    return (this.collaboration && this.collaboration.studies.length > 0) || false;
  }

  get shouldShowDatabaseStep(): boolean {
    return !this.function || (!!this.function?.databases && this.function.databases.length > 0);
  }

  get shouldShowPreprocessorStep(): boolean {
    if (!this.algorithm || !this.function) return true;
    return this.algorithm.select !== undefined && this.algorithm.select.length > 0 && this.shouldShowDatabaseStep;
  }

  get shouldShowFilterStep(): boolean {
    if (!this.algorithm || !this.function) return true;
    return this.algorithm.filter !== undefined && this.algorithm.filter.length > 0 && this.shouldShowDatabaseStep;
  }

  get shouldShowParameterStep(): boolean {
    return !this.function || (!!this.function && !!this.function.arguments && this.function.arguments.length > 0);
  }

  async setupRepeatTask(taskID: string): Promise<void> {
    this.isLoadingColumns = true;
    this.repeatedTask = await this.taskService.getTask(Number(taskID));
    if (!this.repeatedTask) {
      return;
    }

    // set study step
    if (this.repeatedTask.study?.id) {
      this.studyForm.controls.studyOrCollabID.setValue(StudyOrCollab.Study + this.repeatedTask.study.id.toString());
      await this.handleStudyChange(this.repeatedTask.study.id);
    } else {
      this.studyForm.controls.studyOrCollabID.setValue(StudyOrCollab.Collaboration + this.collaboration?.id.toString());
      await this.handleStudyChange(null);
    }

    // set algorithm step
    this.functionForm.controls.name.setValue(this.repeatedTask.name);
    this.functionForm.controls.description.setValue(this.repeatedTask.description);
    let algorithm = this.algorithms.find((_) => _.image === this.repeatedTask?.image);
    if (!algorithm && this.repeatedTask?.image.includes('@sha256:')) {
      // get algorithm including digest
      algorithm = this.algorithms.find((_) => `${_.image}@${_.digest}` === this.repeatedTask?.image);
    }
    if (!algorithm || !algorithm.algorithm_store_id) return;
    await this.handleAlgorithmChange(algorithm.id, algorithm.algorithm_store_id);
    // set function step
    if (!this.repeatedTask.input) return;

    const func =
      this.functions.find(
        (_) =>
          _.name === this.repeatedTask?.input?.method &&
          _.algorithm_id == algorithm.id &&
          _.algorithm_store_id == algorithm.algorithm_store_id
      ) || null;
    if (!func) return;
    this.functionForm.controls.algorithmFunctionSpec.setValue(this.getAlgorithmFunctionSpec(func));
    await this.handleFunctionChange(this.repeatedTask.input?.method, algorithm.id, algorithm.algorithm_store_id);
    if (!this.function) return;
    const organizationIDs = this.repeatedTask.runs.map((_) => _.organization?.id).toString();
    this.functionForm.controls.organizationIDs.setValue(organizationIDs);

    // Note: the database step is not setup here because the database child
    // component may not yet be initialized when we get here. Instead, we
    // setup the database step in the database child component when it is
    // initialized in the function handleDatabaseStepInitialized().
    // However, we need to be sure that the database child component is initialized
    // because we need the columns to be loaded before we set up the parameters, so we
    // wait for that to happen
    while (!this.isLoadingColumns) {
      await new Promise((f) => setTimeout(f, 200));
    }

    // set parameter step
    for (const parameter of this.repeatedTask.input?.parameters || []) {
      const argument: Argument | undefined = this.function?.arguments.find((_) => _.name === parameter.label);
      // check if value is an object
      if (!argument) {
        // this should never happen, but fallback is simply try to fill value in
        this.parameterForm.get(parameter.label)?.setValue(parameter.value);
      } else if (argument.type === ArgumentType.Json) {
        this.parameterForm.get(parameter.label)?.setValue(JSON.stringify(parameter.value));
      } else if (
        argument.type === ArgumentType.FloatList ||
        argument.type === ArgumentType.IntegerList ||
        argument.type == ArgumentType.StringList
      ) {
        const controls = this.getFormArrayControls(argument);
        let isFirst = true;
        for (const value of parameter.value) {
          if (!isFirst) controls.push(this.getNewControlForInputList(argument));
          controls[controls.length - 1].setValue(value);
          isFirst = false;
        }
      } else if (argument.type === ArgumentType.Boolean) {
        this.parameterForm.get(parameter.label)?.setValue(parameter.value ? true : false);
      } else {
        this.parameterForm.get(parameter.label)?.setValue(parameter.value);
      }
    }

    // go to last step
    // TODO this can still be NULL when we get here, then it doesn't work
    if (this.myStepper?._steps) {
      for (let idx = 0; idx < this.myStepper?._steps.length || 0; idx++) {
        this.myStepper?.next();
      }
    }
  }

  search() {
    const value = this.functionForm.controls.algorithmFunctionSearch.value;
    this.filteredFunctions = this.functions.filter((func) => {
      const curAlgorithm = this.algorithms.find((_) => _.id === func.algorithm_id && _.algorithm_store_id == func.algorithm_store_id);
      const storeName = curAlgorithm ? this.getAlgorithmStoreName(curAlgorithm) : '';
      return [func.algorithm_name, func.type, storeName, func.display_name, func.name].some((val) =>
        val?.toLowerCase()?.includes(value.toLowerCase())
      );
    });
  }

  clearFunctionSearchInput() {
    this.functionForm.controls.algorithmFunctionSearch.setValue('');
    this.search();
  }

  getFunctionOptionLabel(func: AlgorithmFunctionExtended): string {
    const curAlgorithm = this.algorithms.find((_) => _.id === func.algorithm_id && _.algorithm_store_id == func.algorithm_store_id);
    const storeName = curAlgorithm ? this.getAlgorithmStoreName(curAlgorithm) : '';
    return `${this.getDisplayName(func)} <div class="detail-txt"> | ${func.algorithm_name}, ${storeName}, ${func.type}</div>`;
  }

  getAlgorithmFunctionSpec(func: AlgorithmFunctionExtended): string {
    return `${func.name}__${func.algorithm_id}__${func.algorithm_store_id}`;
  }

  async handleDatabaseStepInitialized(): Promise<void> {
    if (!this.repeatedTask || !this.function) return;
    // This function is run when the database child component is initialized,
    // but it may still be null when we get here. If it is null, we wait a bit
    // and then (recursively) try again.
    if (!this.databaseStepComponent) {
      await new Promise((f) => setTimeout(f, 200));
      this.handleDatabaseStepInitialized();
      return;
    }

    // Now, setup the database step
    // set database step for task repeat
    this.databaseStepComponent?.setDatabasesFromPreviousTask(this.repeatedTask?.databases, this.function?.databases);

    // retrieve column names as we dont go through the HTML steppers manually
    // (where this is otherwise triggered)
    this.retrieveColumns();

    // TODO repeat preprocessing and filtering when backend is ready
  }

  async handleSubmit(): Promise<void> {
    if (this.isSubmitting) return;
    this.isSubmitting = true;
    try {
      await this.submitTask();
    } catch (error) {
      this.isSubmitting = false;
    }
  }

  async submitTask(): Promise<void> {
    if (
      this.studyForm.invalid ||
      this.functionForm.invalid ||
      this.databaseForm.invalid ||
      this.preprocessingForm.invalid ||
      this.filterForm.invalid ||
      this.parameterForm.invalid
    ) {
      return;
    }

    const selectedOrganizations = Array.isArray(this.functionForm.controls.organizationIDs.value)
      ? this.functionForm.controls.organizationIDs.value
      : [this.functionForm.controls.organizationIDs.value];

    const taskDatabases: TaskDatabase[] = getTaskDatabaseFromForm(this.function, this.databaseForm);

    // setup input for task. Parse string to JSON if needed
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const kwargs: any = {};
    this.function?.arguments.forEach((arg) => {
      Object.keys(this.parameterForm.controls).forEach((control) => {
        if (control === arg.name) {
          const value = this.parameterForm.get(control)?.value;
          if (arg.is_frontend_only || (arg.has_default_value && value === null)) {
            return; // note that within .forEach, return is like continue
          } else if (arg.type === ArgumentType.Json) {
            kwargs[arg.name] = JSON.parse(value);
          } else if (arg.type === ArgumentType.Float || arg.type === ArgumentType.Integer) {
            kwargs[arg.name] = Number(value);
          } else if (
            arg.type === ArgumentType.FloatList ||
            arg.type === ArgumentType.IntegerList ||
            arg.type === ArgumentType.OrganizationList
          ) {
            kwargs[arg.name] = value.map((_: string) => Number(_));
          } else {
            kwargs[arg.name] = value;
          }
        }
      });
    });
    const input: CreateTaskInput = {
      method: this.function?.name || '',
      kwargs: kwargs
    };
    // encrypt the input for each organization
    const inputPerOrg: { [key: string]: string } = {};
    const inputStringified = btoa(JSON.stringify(input)) || '';
    for (const organizationID of selectedOrganizations) {
      const org_input = await this.encryptionService.encryptData(inputStringified, organizationID);
      inputPerOrg[organizationID] = org_input;
    }

    let image = this.algorithm?.image || '';
    if (this.algorithm?.digest) {
      image = `${image}@${this.algorithm?.digest}`;
    }

    const createTask: CreateTask = {
      name: this.functionForm.controls.name.value,
      description: this.functionForm.controls.description.value,
      image: image,
      collaboration_id: this.collaboration?.id || -1,
      databases: taskDatabases,
      store_id: this.algorithm?.algorithm_store_id || -1,
      server_url: environment.server_url,
      organizations: selectedOrganizations.map((organizationID) => {
        return {
          id: Number.parseInt(organizationID),
          input: inputPerOrg[organizationID] || ''
        };
      })
      //TODO: Add preprocessing and filtering when backend is ready
    };

    if (this.studyForm.controls['studyOrCollabID'].value.startsWith(StudyOrCollab.Study)) {
      createTask.study_id = Number(this.studyForm.controls['studyOrCollabID'].value.substring(StudyOrCollab.Study.length));
    }

    const newTask = await this.taskService.createTask(createTask);
    if (newTask) {
      this.router.navigate([routePaths.task, newTask.id]);
    }
  }

  async retrieveColumns(): Promise<void> {
    this.isLoadingColumns = true;
    if (!this.node) return;

    // collect data to collect columns from database
    const taskDatabases = getTaskDatabaseFromForm(this.function, this.databaseForm);
    const databases = getDatabaseTypesFromForm(this.function, this.databaseForm, this.databaseStepComponent?.availableDatabases || []);

    // the other and omop database types do not make use of the wrapper to load their
    // data, so we cannot process them in this way. This will be improved when sessions
    // are implemented
    const database = databases[0];
    if (database.type == 'other' || database.type == 'omop') {
      this.isLoadingColumns = false;
      return;
    }

    // TODO modify when choosing database for preprocessing is implemented
    const taskDatabase = taskDatabases[0];

    const input = { method: 'column_headers' };

    const columnRetrieveData: ColumnRetrievalInput = {
      collaboration_id: this.collaboration?.id || -1,
      db_label: taskDatabase.label,
      organizations: [
        {
          id: this.node.organization.id,
          input: btoa(JSON.stringify(input)) || ''
        }
      ]
    };
    if (taskDatabase.query) {
      columnRetrieveData.query = taskDatabase.query;
    }
    if (taskDatabase.sheet_name) {
      columnRetrieveData.sheet_name = taskDatabase.sheet_name;
    }

    // call /column endpoint. This returns either a list of columns or a task
    // that will retrieve the columns
    // TODO enable user to exit requesting column names if it takes too long
    const columnsOrTask = await this.taskService.getColumnNames(columnRetrieveData);
    if (columnsOrTask.columns) {
      this.columns = columnsOrTask.columns;
    } else {
      // a task has been started to retrieve the columns
      const task = await this.taskService.waitForResults(columnsOrTask.id);
      this.columns = task.results?.[0].decoded_result || JSON.parse('');
    }
    this.isLoadingColumns = false;
    this.hasLoadedColumns = true;
  }

  shouldShowParameterSimpleInput(argument: Argument): boolean {
    return (
      !this.shouldShowColumnDropdown(argument) &&
      !this.shouldShowOrganizationDropdown(argument) &&
      !this.shouldShowParameterBooleanInput(argument) &&
      !this.shouldShowParameterJsonInput(argument)
    );
  }

  shouldIncludeFormField(argument: Argument): boolean {
    return (
      !this.shouldShowParameterBooleanInput(argument) &&
      !this.shouldShowMultipleInput(argument) &&
      !this.shouldShowParameterJsonInput(argument)
    );
  }

  shouldShowMultipleInput(argument: Argument): boolean {
    return (
      argument.type === this.argumentType.IntegerList ||
      argument.type === this.argumentType.FloatList ||
      argument.type === this.argumentType.StringList ||
      (argument.type === this.argumentType.ColumnList && this.columns.length === 0 && this.hasLoadedColumns)
    );
  }

  shouldShowParameterJsonInput(argument: Argument): boolean {
    return argument.type === this.argumentType.Json;
  }

  shouldShowParameterBooleanInput(argument: Argument): boolean {
    return argument.type === this.argumentType.Boolean;
  }

  shouldShowOrganizationDropdown(argument: Argument): boolean {
    return argument.type === this.argumentType.Organization || argument.type === this.argumentType.OrganizationList;
  }

  shouldShowColumnDropdown(argument: Argument): boolean {
    return (
      (argument.type === this.argumentType.Column || argument.type === this.argumentType.ColumnList) &&
      (this.columns.length > 0 || this.isLoadingColumns)
    );
  }

  containsColumnArguments(): boolean {
    return this.function?.arguments.some((arg) => arg.type === this.argumentType.Column) || false;
  }

  shouldShowColumnDropdownForAnyArg(): boolean {
    return this.containsColumnArguments();
  }

  addInputFieldForArg(argument: Argument): void {
    (this.parameterForm.get(argument.name) as FormArray).push(this.getNewControlForInputList(argument));
  }

  removeInputFieldForArg(argument: Argument, index: number): void {
    (this.parameterForm.get(argument.name) as FormArray).removeAt(index);
  }

  getFormArrayControls(argument: Argument) {
    if ((this.parameterForm.get(argument.name) as FormArray).controls === undefined) {
      const initialControl = argument.has_default_value ? [] : [this.getNewControlForInputList(argument)];
      this.parameterForm.setControl(argument.name, this.fb.array(initialControl));
    }
    return (this.parameterForm.get(argument.name) as FormArray).controls;
  }

  private getNewControlForInputList(argument: Argument): AbstractControl {
    if (argument.type === this.argumentType.IntegerList) {
      return this.fb.control('', [Validators.required, Validators.pattern(integerRegex)]);
    } else if (argument.type === this.argumentType.FloatList) {
      return this.fb.control('', [Validators.required, Validators.pattern(floatRegex)]);
    } else {
      return this.fb.control('', Validators.required);
    }
  }

  // compare function for mat-select
  compareIDsForSelection(id1: number | string, id2: number | string): boolean {
    // The mat-select object set from typescript only has an ID set. Compare that with the ID of the
    // organization object from the collaboration
    if (typeof id1 === 'number') {
      id1 = id1.toString();
    }
    if (typeof id2 === 'number') {
      id2 = id2.toString();
    }
    return id1 === id2;
  }

  sortArgumentsForDisplay(arguments_: Argument[] | undefined) {
    if (!arguments_) return undefined;
    // first order by ID
    arguments_ = arguments_.sort((a, b) => a.id - b.id);
    // Sort the parameters of the function such that parameters that are conditional on
    // others are just behind those
    for (let idx = 0; idx < arguments_.length; idx++) {
      const arg = arguments_[idx];
      if (arg?.conditional_on_id) {
        // Find the idx in the list of the one it is conditional on
        const conditionalIdx = arguments_.findIndex((condArg) => condArg.id === arg.conditional_on_id);
        if (conditionalIdx > idx) {
          [arguments_[idx], arguments_[conditionalIdx]] = [arguments_[conditionalIdx], arguments_[idx]];
          idx = -1;
        }
      }
    }
    return arguments_;
  }

  async selectedJsonFile(event: Event, argument: Argument): Promise<void> {
    const selectedFile = (event.target as HTMLInputElement).files?.item(0) || null;

    if (!selectedFile) return;
    const fileData = await readFile(selectedFile);

    this.parameterForm.controls[`${argument.name}`].setValue(fileData || '');
    this.parameterForm.controls[`${argument.name}_jsonFileName`].setValue(selectedFile.name || '');
  }

  getJsonFileName(argument: Argument): string {
    return this.parameterForm.controls[`${argument.name}_jsonFileName`].value;
  }

  compareStudyOrCollabForSelection(val1: number | string, val2: number | string): boolean {
    return val1 === val2;
  }

  async setOrganizations() {
    if (!this.collaboration) return;

    if (this.study) {
      this.organizations = await this.organizationService.getOrganizations({ study_id: this.study.id });
    } else {
      this.organizations = this.collaboration.organizations;
    }
  }

  hasAlgorithmStores(): boolean {
    return this.collaboration?.algorithm_stores ? this.collaboration.algorithm_stores.length > 0 : false;
  }

  hasOnlineNode(): boolean {
    return this.node ? this.node?.status === 'online' : false;
  }

  hasAlgorithms(): boolean {
    return this.algorithms.length > 0;
  }

  getAlgorithmStoreName(algorithm: Algorithm): string {
    if (this.collaboration?.algorithm_stores && this.collaboration.algorithm_stores.length > 1) {
      const store_name = this.collaboration.algorithm_stores.find((_) => _.url === algorithm.algorithm_store_url)?.name;
      if (store_name) {
        return `${store_name}`;
      }
    }
    return '';
  }

  getDisplayName(obj: AlgorithmFunction | Argument): string {
    return obj.display_name && obj.display_name != '' ? obj.display_name : obj.name;
  }

  shouldDisplayArgument(function_: AlgorithmFunction | null, argument: Argument): boolean {
    // argument should not be displayed if it is conditional on another and the
    // condition is not fulfilled
    if (!argument.conditional_on_id) {
      return true;
    }
    const conditionalArg = function_?.arguments.find((arg: Argument) => arg.id === argument.conditional_on_id);
    if (!conditionalArg) {
      return true;
    }
    let curConditionalValue = this.parameterForm.get(conditionalArg.name)?.value;
    // cast the values (if necessary)
    let conditionDatabaseValue: string | number | boolean | undefined;
    if (conditionalArg.type === ArgumentType.Boolean) {
      conditionDatabaseValue = isTruthy(argument.conditional_value);
      curConditionalValue = isTruthy(curConditionalValue);
    } else if (conditionalArg.type === ArgumentType.Float || conditionalArg.type === ArgumentType.Integer) {
      conditionDatabaseValue = Number(argument.conditional_value);
      curConditionalValue = Number(curConditionalValue);
    } else {
      conditionDatabaseValue = argument.conditional_value;
    }
    // evaluate the condition
    if (argument.conditional_operator === ConditionalArgComparatorType.Equal) {
      return conditionDatabaseValue === curConditionalValue;
    } else if (argument.conditional_operator === ConditionalArgComparatorType.NotEqual) {
      return conditionDatabaseValue !== curConditionalValue;
    } else if (conditionDatabaseValue) {
      if (argument.conditional_operator === ConditionalArgComparatorType.GreaterThan) {
        return conditionDatabaseValue > curConditionalValue;
      } else if (argument.conditional_operator === ConditionalArgComparatorType.GreaterThanOrEqual) {
        return conditionDatabaseValue >= curConditionalValue;
      } else if (argument.conditional_operator === ConditionalArgComparatorType.LessThan) {
        return conditionDatabaseValue < curConditionalValue;
      } else if (argument.conditional_operator === ConditionalArgComparatorType.LessThanOrEqual) {
        return conditionDatabaseValue <= curConditionalValue;
      }
    }
    // fallback - just display it, but should never get here
    return true;
  }

  private async initData(): Promise<void> {
    this.collaboration = this.chosenCollaborationService.collaboration$.value;
    const algorithmsObj = await this.algorithmService.getAlgorithms();
    this.algorithms = algorithmsObj;
    this.functions = algorithmsObj.flatMap((curAlgorithm) => {
      return (
        curAlgorithm.functions
          // TODO v5+ remove the func.standalone === undefined check. After v5+ the standalone property should be set for all functions
          .filter((func) => func.standalone || func.standalone === undefined)
          .map((func) => {
            return {
              ...func,
              algorithm_id: curAlgorithm.id,
              algorithm_name: curAlgorithm.name,
              algorithm_store_id: curAlgorithm.algorithm_store_id
            };
          })
      );
    });
    this.filteredFunctions = this.functions;
    this.node = await this.getOnlineNode();

    // set default for study step: full collaboration (this is not visible but required
    // if there are no studies defined to have a valid form)
    this.studyForm.controls['studyOrCollabID'].setValue(StudyOrCollab.Collaboration + this.collaboration?.id.toString());
    this.setOrganizations();

    this.studyForm.controls['studyOrCollabID'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (studyID) => {
      if (studyID.startsWith(StudyOrCollab.Study)) {
        this.handleStudyChange(Number(studyID.substring(StudyOrCollab.Study.length)));
      }
    });

    this.functionForm.controls.algorithmFunctionSpec.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (algorithmFunctionSpec) => {
        const [functionName, algorithmID, algorithmStoreID] = algorithmFunctionSpec.split('__');
        this.handleFunctionChange(String(functionName), Number(algorithmID), Number(algorithmStoreID));
      });

    this.nodeStatusUpdateSubscription = this.socketioConnectService
      .getNodeStatusUpdates()
      .subscribe((nodeStatusUpdate: NodeOnlineStatusMsg | null) => {
        if (nodeStatusUpdate) this.onNodeStatusUpdate(nodeStatusUpdate);
      });

    this.isNgInitDone = true;

    if (!this.isTaskRepeat) this.isLoading = false;
    this.isDataInitialized = true;
  }

  private async handleStudyChange(studyID: number | null): Promise<void> {
    // clear relevant forms
    this.clearFunctionStep();
    this.clearDatabaseStep();

    // select study
    if (studyID) {
      this.study = this.collaboration?.studies.find((_) => _.id === studyID) || null;
    } else {
      // by deselecting study, defaults to entire collaboration
      this.study = null;
    }
    this.setOrganizations();
  }

  private async handleAlgorithmChange(algorithmID: number, algoStoreID: number): Promise<void> {
    //Clear form
    this.clearFunctionStep();
    this.clearDatabaseStep();
    this.clearPreprocessingStep();
    this.clearFilterStep();
    this.clearParameterStep();

    //Get selected algorithm
    this.algorithm = this.algorithms.find((_) => _.id === algorithmID && _.algorithm_store_id == algoStoreID) || null;
  }

  private handleFunctionChange(functionName: string, algorithmID: number, algoStoreID: number): void {
    // Clear form
    this.clearFunctionStep(); //Also clear function step, so user needs to reselect organization
    this.clearDatabaseStep();
    this.clearPreprocessingStep(); // this depends on the database, so it should be cleared
    this.clearFilterStep();
    this.clearParameterStep();

    this.algorithm = this.algorithms.find((_) => _.id === algorithmID && _.algorithm_store_id == algoStoreID) || null;
    // Get selected function
    const selectedFunction =
      this.functions.find((_) => _.name === functionName && _.algorithm_id == algorithmID && _.algorithm_store_id == algoStoreID) || null;

    if (selectedFunction) {
      // Add form controls for parameters for selected function
      addParameterFormControlsForFunction(selectedFunction, this.parameterForm);
    }

    // Delay setting function, so that form controls are added
    this.function = selectedFunction;
  }

  private async getOnlineNode(): Promise<BaseNode | null> {
    //Get all nodes for chosen collaboration
    const nodes = await this.getNodes();

    //Find a random node that is online and that has shared their configuration
    const node = nodes?.find((_) => _.status === 'online' && _.config.length > 0) || null;
    if (!node) {
      // if there is no node that has shared its configuration, go for the next best
      // thing: an online node (this will not work for tasks that require databases
      // but it is better than nothing)
      return nodes?.find((_) => _.status === 'online') || null;
    }
    return node;
  }

  private async getNodes(): Promise<BaseNode[] | null> {
    return await this.nodeService.getNodes({
      collaboration_id: this.collaboration?.id.toString() || ''
    });
  }

  private clearFunctionStep(): void {
    this.functionForm.controls.organizationIDs.reset();
    Object.keys(this.databaseForm.controls).forEach((control) => {
      this.parameterForm.removeControl(control);
    });
  }

  private clearDatabaseStep(): void {
    this.databaseStepComponent?.reset();
  }

  private clearPreprocessingStep(): void {
    this.preprocessingStep?.clear();
    this.columns = [];
  }

  private clearFilterStep(): void {
    this.filterStep?.clear();
  }

  private clearParameterStep(): void {
    this.parameterForm = this.fb.nonNullable.group({});
  }

  private async onNodeStatusUpdate(nodeStatusUpdate: NodeOnlineStatusMsg): Promise<void> {
    // check if currently selected node is the one that came online/offline
    if (this.node && this.node.id === nodeStatusUpdate.id) {
      this.node.status = nodeStatusUpdate.online ? NodeStatus.Online : NodeStatus.Offline;
    }
    // if no node is selected or the selected node is offline, try to get an online node
    if (!this.node || this.node.status === NodeStatus.Offline) {
      this.node = await this.getOnlineNode();
    }
    if (this.node && nodeStatusUpdate.online) {
      // Our selected node just came online, and we need to refresh which
      // databases are available. These are obtained from the configuration that
      // the node shares with the server after coming online. So we need to wait
      // a bit and then refresh the node to get the node configuration
      let attempts = 0;
      let success = false;
      while (attempts < MAX_ATTEMPTS_RENEW_NODE) {
        await new Promise((f) => setTimeout(f, SECONDS_BETWEEN_ATTEMPTS_RENEW_NODE * 1000));
        this.node = await this.getOnlineNode();
        if (this.node && this.node.config.length > 0) {
          // stop if we have configuration info
          success = true;
          break;
        }
        attempts++;
      }
      if (!success) {
        this.snackBarService.showMessage(this.translateService.instant('task-create.step-database.error-db-update'));
      }
    }
  }
}
