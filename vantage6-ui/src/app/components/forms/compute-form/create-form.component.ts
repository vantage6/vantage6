import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  HostBinding,
  Input,
  input,
  OnDestroy,
  OnInit,
  Output,
  ViewChild
} from '@angular/core';
import { AbstractControl, FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm, ArgumentType, AlgorithmFunction, Argument, FunctionType } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { BaseNode, NodeStatus } from 'src/app/models/api/node.model';
import { ColumnRetrievalInput, CreateTask, CreateTaskInput, Task, TaskDatabase } from 'src/app/models/api/task.models';
import { TaskService } from 'src/app/services/task.service';
import { routePaths } from 'src/app/routes';
import { Router, RouterLink } from '@angular/router';
import { PreprocessingStepComponent } from './steps/preprocessing-step/preprocessing-step.component';
import {
  addParameterFormControlsForFunction,
  getTaskDatabaseFromForm,
  getDatabaseTypesFromForm
} from 'src/app/pages/analyze/task/task.helper';
import { DatabaseStepComponent } from './steps/database-step/database-step.component';
import { FilterStepComponent } from './steps/filter-step/filter-step.component';
import { NodeService } from 'src/app/services/node.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { MatStep, MatStepper } from '@angular/material/stepper';
import { SnackbarService } from 'src/app/services/snackbar.service';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Collaboration } from 'src/app/models/api/collaboration.model';
import { BaseStudy, StudyOrCollab } from 'src/app/models/api/study.model';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { MAX_ATTEMPTS_RENEW_NODE, SECONDS_BETWEEN_ATTEMPTS_RENEW_NODE } from 'src/app/models/constants/wait';
import { floatRegex, integerRegex } from 'src/app/helpers/regex.helper';
import { EncryptionService } from 'src/app/services/encryption.service';
import { environment } from 'src/environments/environment';
import { BaseSession, Dataframe } from 'src/app/models/api/session.models';
import { SessionService } from 'src/app/services/session.service';
import { AvailableSteps, FormCreateOutput } from 'src/app/models/forms/create-form.model';
import { PageHeaderComponent } from '../../page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { AlertComponent } from '../../alerts/alert/alert.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatOption, MatSelect } from '@angular/material/select';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatSpinner } from '@angular/material/progress-spinner';
import { NgFor, NgIf } from '@angular/common';

@Component({
  selector: 'app-create-form',
  templateUrl: './create-form.component.html',
  styleUrls: ['./create-form.component.scss'],
  imports: [
    PageHeaderComponent,
    AlertComponent,
    DatabaseStepComponent,
    PreprocessingStepComponent,
    FilterStepComponent,
    MatCard,
    MatCardContent,
    MatStepper,
    MatIcon,
    MatStep,
    MatFormField,
    MatLabel,
    MatSelect,
    MatOption,
    MatCheckbox,
    MatSpinner,
    TranslateModule,
    RouterLink,
    ReactiveFormsModule,
    NgIf,
    NgFor
  ]
})
export class FormCreateComponent implements OnInit, OnDestroy, AfterViewInit {
  @HostBinding('class') class = 'card-container';

  @Input() formTitle: string = '';
  @Input() sessionId?: string = '';

  // TODO(BART/RIAN) RIAN: Somehow we need to be able to calculate which step is first and which is last in order to conditionally add the back or next button.
  @Input() availableSteps: AvailableSteps = {
    session: false,
    study: false,
    package: false,
    function: false,
    database: false,
    dataframe: false,
    preprocessing: false,
    filter: false,
    parameter: false
  };

  @Output() public onSubmit: EventEmitter<FormCreateOutput> = new EventEmitter<FormCreateOutput>();
  @Output() public onCancel: EventEmitter<void> = new EventEmitter();

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

  sessions: BaseSession[] = [];
  session: BaseSession | null = null;
  study: BaseStudy | null = null;
  algorithms: Algorithm[] = [];
  algorithm: Algorithm | null = null;
  collaboration?: Collaboration | null = null;
  organizations: BaseOrganization[] = [];
  function: AlgorithmFunction | null = null;
  dataframes: Dataframe[] = [];
  node: BaseNode | null = null;
  columns: string[] = [];
  isStudyCompleted: boolean = false;
  isLoading: boolean = true;
  isLoadingColumns: boolean = false;
  hasLoadedColumns: boolean = false;
  isSubmitting: boolean = false;
  isTaskRepeat: boolean = false;
  isDataInitialized: boolean = false;
  isNgInitDone: boolean = false;
  repeatedTask: Task | null = null;

  sessionForm = this.fb.nonNullable.group({
    sessionID: ['', Validators.required]
  });
  studyForm = this.fb.nonNullable.group({
    studyOrCollabID: [{ value: '', disabled: false }, Validators.required]
  });
  packageForm = this.fb.nonNullable.group({
    algorithmSpec: ['', Validators.required],
    name: ['', Validators.required],
    description: ''
  });
  functionForm = this.fb.nonNullable.group({
    functionName: ['', Validators.required],
    organizationIDs: [[''], Validators.required]
  });
  databaseForm = this.fb.nonNullable.group({});
  dataframeForm = this.fb.nonNullable.group({
    dataframeHandle: ['', Validators.required]
  });
  preprocessingForm = this.fb.array([]);
  filterForm = this.fb.array([]);
  parameterForm: FormGroup = this.fb.nonNullable.group({});

  private nodeStatusUpdateSubscription?: Subscription;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private changeDetectorRef: ChangeDetectorRef,
    private sessionService: SessionService,
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

  get shouldShowDataframeStep(): boolean {
    return !this.session || (!!this.dataframes && this.dataframes.length > 0);
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

    this.sessionForm.controls.sessionID.setValue(this.repeatedTask.session.id.toString());

    // set study step
    if (this.repeatedTask.study?.id) {
      this.studyForm.controls.studyOrCollabID.setValue(StudyOrCollab.Study + this.repeatedTask.study.id.toString());
      await this.handleStudyChange(this.repeatedTask.study.id);
    } else {
      this.studyForm.controls.studyOrCollabID.setValue(StudyOrCollab.Collaboration + this.collaboration?.id.toString());
      await this.handleStudyChange(null);
    }

    // set algorithm step
    this.packageForm.controls.name.setValue(this.repeatedTask.name);
    this.packageForm.controls.description.setValue(this.repeatedTask.description);
    let algorithm = this.algorithms.find((_) => _.image === this.repeatedTask?.image);
    if (!algorithm && this.repeatedTask?.image.includes('@sha256:')) {
      // get algorithm including digest
      algorithm = this.algorithms.find((_) => `${_.image}@${_.digest}` === this.repeatedTask?.image);
    }
    if (!algorithm || !algorithm.algorithm_store_id) return;
    const algoSpec = this.getAlgoSpec(algorithm);
    this.packageForm.controls.algorithmSpec.setValue(algoSpec);
    await this.handleAlgorithmChange(algorithm.id, algorithm.algorithm_store_id);
    // set function step
    if (!this.repeatedTask.input) return;
    this.functionForm.controls.functionName.setValue(this.repeatedTask?.input?.method);
    await this.handleFunctionChange(this.repeatedTask.input?.method);
    if (!this.function) return;
    const organizationIDs = this.repeatedTask.runs.map((_) => _.organization?.id?.toString() ?? '').filter((value) => value);
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

  getAlgoSpec(algorithm: Algorithm): string {
    return `${algorithm.id}_${algorithm.algorithm_store_id}`;
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

  isFormInvalid(): boolean {
    return (
      (this.availableSteps.session && this.sessionForm.invalid) ||
      (this.availableSteps.study && this.studyForm.invalid) ||
      (this.availableSteps.package && this.packageForm.invalid) ||
      (this.availableSteps.function && this.functionForm.invalid) ||
      (this.availableSteps.database && this.databaseForm.invalid) ||
      (this.availableSteps.preprocessing && this.preprocessingForm.invalid) ||
      (this.availableSteps.filter && this.filterForm.invalid) ||
      (this.availableSteps.parameter && this.parameterForm.invalid)
    );
  }

  async handleSubmit(): Promise<void> {
    if (this.isSubmitting) return;
    if (this.isFormInvalid()) return;
    this.isSubmitting = true;
    try {
      await this.submitTask();
    } catch (error) {
      this.isSubmitting = false;
    }
  }

  async submitTask(): Promise<void> {
    const taskDatabases: TaskDatabase[] = getTaskDatabaseFromForm(this.function, this.databaseForm);

    // setup input for task. Parse string to JSON if needed
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const kwargs: any = {};
    this.function?.arguments.forEach((arg) => {
      Object.keys(this.parameterForm.controls).forEach((control) => {
        if (control === arg.name) {
          const value = this.parameterForm.get(control)?.value;
          if (arg.has_default_value && value === null) {
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

    const selectedOrganizations = Array.isArray(this.functionForm.controls.organizationIDs.value)
      ? this.functionForm.controls.organizationIDs.value
      : [this.functionForm.controls.organizationIDs.value];
    // encrypt the input for each organization
    const inputPerOrg: { [key: string]: string } = {};
    const inputStringified = btoa(JSON.stringify(input)) || '';
    for (const organizationID of selectedOrganizations) {
      const org_input = await this.encryptionService.encryptData(inputStringified, Number(organizationID));
      inputPerOrg[organizationID] = org_input;
    }

    let image = this.algorithm?.image || '';
    if (this.algorithm?.digest) {
      image = `${image}@${this.algorithm?.digest}`;
    }

    const formCreateOutput: FormCreateOutput = {
      name: this.packageForm.controls.name.value,
      description: this.packageForm.controls.description.value,
      image: image,
      session_id: Number.parseInt(this.sessionForm.controls.sessionID.value),
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
    };

    if (this.studyForm.controls['studyOrCollabID'].value.startsWith(StudyOrCollab.Study)) {
      formCreateOutput.study_id = Number(this.studyForm.controls['studyOrCollabID'].value.substring(StudyOrCollab.Study.length));
    }

    this.onSubmit.next(formCreateOutput);
  }

  handleCancel(): void {
    this.onCancel.emit();
  }

  async retrieveColumns(): Promise<void> {
    // TODO(BART/RIAN) RIAN: Wanneer er een dataframe is kunnen de colums pas worden opgehaald.
    //
    //
    //
    // this.isLoadingColumns = true;
    // if (!this.node) return;
    // // collect data to collect columns from database
    // const taskDatabases = getTaskDatabaseFromForm(this.function, this.databaseForm);
    // const databases = getDatabaseTypesFromForm(this.function, this.databaseForm, this.databaseStepComponent?.availableDatabases || []);
    // // the other and omop database types do not make use of the wrapper to load their
    // // data, so we cannot process them in this way. This will be improved when sessions
    // // are implemented
    // const database = databases[0];
    // if (database.type == 'other' || database.type == 'omop') {
    //   this.isLoadingColumns = false;
    //   return;
    // }
    // // TODO modify when choosing database for preprocessing is implemented
    // const taskDatabase = taskDatabases[0];
    // const input = { method: 'column_headers' };
    // const columnRetrieveData: ColumnRetrievalInput = {
    //   collaboration_id: this.collaboration?.id || -1,
    //   db_label: taskDatabase.label,
    //   organizations: [
    //     {
    //       id: this.node.organization.id,
    //       input: btoa(JSON.stringify(input)) || ''
    //     }
    //   ]
    // };
    // if (taskDatabase.query) {
    //   columnRetrieveData.query = taskDatabase.query;
    // }
    // if (taskDatabase.sheet_name) {
    //   columnRetrieveData.sheet_name = taskDatabase.sheet_name;
    // }
    // // call /column endpoint. This returns either a list of columns or a task
    // // that will retrieve the columns
    // // TODO enable user to exit requesting column names if it takes too long
    // const columnsOrTask = await this.taskService.getColumnNames(columnRetrieveData);
    // if (columnsOrTask.columns) {
    //   this.columns = columnsOrTask.columns;
    // } else {
    //   // a task has been started to retrieve the columns
    //   const task = await this.taskService.waitForResults(columnsOrTask.id);
    //   this.columns = task.results?.[0].decoded_result || JSON.parse('');
    // }
    // this.isLoadingColumns = false;
    // this.hasLoadedColumns = true;
  }

  shouldShowParameterSimpleInput(argument: Argument): boolean {
    return (
      !this.shouldShowColumnDropdown(argument) &&
      !this.shouldShowOrganizationDropdown(argument) &&
      !this.shouldShowParameterBooleanInput(argument)
    );
  }

  shouldIncludeFormField(argument: Argument): boolean {
    return !this.shouldShowParameterBooleanInput(argument) && !this.shouldShowMultipleInput(argument);
  }

  shouldShowMultipleInput(argument: Argument): boolean {
    return (
      argument.type === this.argumentType.IntegerList ||
      argument.type === this.argumentType.FloatList ||
      argument.type === this.argumentType.StringList ||
      (argument.type === this.argumentType.ColumnList && this.columns.length === 0 && this.hasLoadedColumns)
    );
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
      this.parameterForm.setControl(argument.name, this.fb.array([this.getNewControlForInputList(argument)]));
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
        return `(${store_name})`;
      }
    }
    return '';
  }

  private async initData(): Promise<void> {
    this.collaboration = this.chosenCollaborationService.collaboration$.value;
    this.sessions = await this.sessionService.getSessions();
    this.algorithms = await this.algorithmService.getAlgorithms();
    this.node = await this.getOnlineNode();

    this.sessionForm.controls['sessionID'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (sessionID) => {
      this.handleSessionChange(sessionID);
    });

    if (this.sessionId) {
      this.sessionForm.controls['sessionID'].setValue(this.sessionId);
    }

    // set default for study step: full collaboration (this is not visible but required
    // if there are no studies defined to have a valid form)
    this.studyForm.controls['studyOrCollabID'].setValue(StudyOrCollab.Collaboration + this.collaboration?.id.toString());
    this.setOrganizations();

    this.studyForm.controls['studyOrCollabID'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (studyID) => {
      if (studyID.startsWith(StudyOrCollab.Study)) {
        this.handleStudyChange(Number(studyID.substring(StudyOrCollab.Study.length)));
      }
      if (studyID) this.isStudyCompleted = true;
    });

    this.packageForm.controls.algorithmSpec.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (algorithmSpec) => {
      const [algorithmID, algorithmStoreID] = algorithmSpec.split('_');
      this.handleAlgorithmChange(Number(algorithmID), Number(algorithmStoreID));
    });

    this.functionForm.controls.functionName.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (functionName) => {
      this.handleFunctionChange(functionName);
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

  private async handleSessionChange(sessionID: string): Promise<void> {
    const sessionIDInt = Number.parseInt(this.sessionForm.controls.sessionID.value) || null;
    this.session = this.sessions?.find((session) => session.id === sessionIDInt) || null;
    this.studyForm.controls.studyOrCollabID.reset();
    this.isStudyCompleted = false;
    if (this.session) {
      if (this.session.study) {
        this.studyForm.get('studyOrCollabID')?.disable();
        this.studyForm.controls['studyOrCollabID'].setValue(StudyOrCollab.Study + this.session.study.id.toString());
        this.handleStudyChange(this.session.study.id);
      } else {
        this.studyForm.get('studyOrCollabID')?.enable();
      }
      this.dataframes = await this.sessionService.getDataframes(this.session.id);
    }
    this.dataframes;
    this.clearFunctionStep();
    this.clearDatabaseStep();
    this.clearPreprocessingStep();
    this.clearFilterStep();
    this.clearParameterStep();
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

  private handleFunctionChange(functionName: string): void {
    //Clear form
    this.clearFunctionStep(); //Also clear function step, so user needs to reselect organization
    this.clearDatabaseStep();
    this.clearPreprocessingStep(); // this depends on the database, so it should be cleared
    this.clearFilterStep();
    this.clearParameterStep();

    //Get selected function
    const selectedFunction = this.algorithm?.functions.find((_) => _.name === functionName) || null;

    if (selectedFunction) {
      //Add form controls for parameters for selected function
      addParameterFormControlsForFunction(selectedFunction, this.parameterForm);
    }

    //Delay setting function, so that form controls are added
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
