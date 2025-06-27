import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  HostBinding,
  Input,
  OnDestroy,
  OnInit,
  Output,
  ViewChild,
  ViewEncapsulation
} from '@angular/core';
import { AbstractControl, FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import {
  Algorithm,
  ArgumentType,
  AlgorithmFunction,
  Argument,
  AlgorithmFunctionExtended,
  ConditionalArgComparatorType,
  FunctionDatabase
} from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { BaseNode, Database, NodeStatus } from 'src/app/models/api/node.model';
import { CreateTaskInput, Task, TaskDatabaseType } from 'src/app/models/api/task.models';
import { TaskService } from 'src/app/services/task.service';
import { routePaths } from 'src/app/routes';
import { Router, RouterLink } from '@angular/router';
import { addParameterFormControlsForFunction } from 'src/app/pages/analyze/task/task.helper';
import { NodeService } from 'src/app/services/node.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { MatStepper, MatStepperIcon, MatStep, MatStepLabel, MatStepperNext, MatStepperPrevious } from '@angular/material/stepper';
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
import { AlgorithmStepType, BaseSession, Dataframe } from 'src/app/models/api/session.models';
import { SessionService } from 'src/app/services/session.service';
import { AvailableSteps, AvailableStepsEnum, FormCreateOutput } from 'src/app/models/forms/create-form.model';
import { PageHeaderComponent } from '../../page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { AlertComponent } from '../../alerts/alert/alert.component';
import { MatFormField, MatLabel, MatSuffix } from '@angular/material/form-field';
import { MatOption, MatSelect } from '@angular/material/select';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { NgFor, NgIf, NgTemplateOutlet } from '@angular/common';
import { MatInput } from '@angular/material/input';
import { MatButton, MatIconButton } from '@angular/material/button';
import { isTruthy } from 'src/app/helpers/utils.helper';
import { HighlightedTextPipe } from 'src/app/pipes/highlighted-text.pipe';
import { readFile } from 'src/app/helpers/file.helper';
import { NumberOnlyDirective } from 'src/app/directives/numberOnly.directive';
import { getDatabasesFromNode } from 'src/app/helpers/node.helper';

@Component({
  selector: 'app-create-form',
  templateUrl: './create-analysis-form.component.html',
  styleUrls: ['./create-analysis-form.component.scss'],
  encapsulation: ViewEncapsulation.None,
  imports: [
    PageHeaderComponent,
    AlertComponent,
    MatCard,
    MatCardContent,
    MatIcon,
    MatStep,
    MatStepper,
    MatStepperIcon,
    MatStepperNext,
    MatStepperPrevious,
    MatStepLabel,
    MatFormField,
    MatLabel,
    MatSelect,
    MatOption,
    MatCheckbox,
    MatProgressSpinner,
    MatInput,
    MatSelect,
    MatButton,
    TranslateModule,
    RouterLink,
    ReactiveFormsModule,
    NgIf,
    NgFor,
    MatIconButton,
    MatSuffix,
    NumberOnlyDirective,
    NgTemplateOutlet,
    HighlightedTextPipe
  ]
})
export class CreateAnalysisFormComponent implements OnInit, OnDestroy, AfterViewInit {
  @HostBinding('class') class = 'card-container';
  availableStepsEnum = AvailableStepsEnum;

  @Input() formTitle: string = '';
  @Input() sessionId?: string = '';
  @Input() allowedTaskTypes?: AlgorithmStepType[];
  @Input() dataframe?: Dataframe | null = null;

  @Input() availableSteps: AvailableSteps = {
    session: false,
    study: false,
    function: false,
    database: false,
    dataframe: false,
    parameter: false
  };

  @Output() public onSubmit: EventEmitter<FormCreateOutput> = new EventEmitter<FormCreateOutput>();
  @Output() public onCancel: EventEmitter<void> = new EventEmitter();

  @ViewChild('stepper') private myStepper: MatStepper | null = null;

  destroy$ = new Subject();
  routes = routePaths;
  argumentType = ArgumentType;
  studyOrCollab = StudyOrCollab;

  sessions: BaseSession[] = [];
  session: BaseSession | null = null;
  study: BaseStudy | null = null;
  algorithms: Algorithm[] = [];
  algorithm: Algorithm | null = null;
  collaboration?: Collaboration | null = null;
  organizations: BaseOrganization[] = [];
  functions: AlgorithmFunctionExtended[] = [];
  filteredFunctions: AlgorithmFunctionExtended[] = [];
  function: AlgorithmFunctionExtended | null = null;
  dataframes: Dataframe[] = [];
  node: BaseNode | null = null;
  availableDatabases: Database[] = [];

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
    studyOrCollabID: [{ value: '', disabled: false }]
  });
  functionForm = this.fb.nonNullable.group({
    algorithmFunctionSpec: ['', Validators.required],
    algorithmFunctionSearch: '',
    organizationIDs: [[''], Validators.required],
    taskName: ['', Validators.required],
    description: ''
  });
  databaseForm = this.fb.nonNullable.group({
    database: ['', Validators.required]
  });
  dataframeForm = this.fb.nonNullable.group({
    dataframeId: ['', Validators.required]
  });
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
    return !this.session || (!!this.function?.databases && this.function.databases.length > 0);
  }

  get shouldShowDatabaseStep(): boolean {
    return !this.function || (!!this.function?.databases && this.function.databases.length > 0);
  }

  get shouldShowParameterStep(): boolean {
    return !this.function || (!!this.function && !!this.function.arguments && this.function.arguments.length > 0);
  }

  isManyDatabaseType(db: FunctionDatabase | undefined): boolean {
    if (!db) return false;
    return db.multiple === true;
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
    this.functionForm.controls.taskName.setValue(this.repeatedTask.name);
    this.functionForm.controls.description.setValue(this.repeatedTask.description);
    let algorithm = this.algorithms.find((_) => _.image === this.repeatedTask?.image);
    if (!algorithm && this.repeatedTask?.image.includes('@sha256:')) {
      // get algorithm including digest
      algorithm = this.algorithms.find((_) => `${_.image}@${_.digest}` === this.repeatedTask?.image);
    }
    if (!algorithm || !algorithm.algorithm_store_id) return;

    await this.handleAlgorithmChange(algorithm.id, algorithm.algorithm_store_id);
    // set function step
    const func =
      this.functions.find(
        (_) =>
          _.name === this.repeatedTask?.method && _.algorithm_id == algorithm.id && _.algorithm_store_id == algorithm.algorithm_store_id
      ) || null;
    if (!func) return;
    this.functionForm.controls.algorithmFunctionSpec.setValue(this.getAlgorithmFunctionSpec(func));
    await this.handleFunctionChange(this.repeatedTask.method, algorithm.id, algorithm.algorithm_store_id);
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

  search() {
    const value = this.functionForm.controls.algorithmFunctionSearch.value;
    this.filteredFunctions = this.functions.filter((func) => {
      const curAlgorithm = this.algorithms.find((_) => _.id === func.algorithm_id && _.algorithm_store_id == func.algorithm_store_id);
      const storeName = curAlgorithm ? this.getAlgorithmStoreName(curAlgorithm) : '';
      return [func.algorithm_name, func.step_type, storeName, func.display_name, func.name].some((val) =>
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
    return `${this.getDisplayName(func)} <div class="detail-txt"> | ${func.algorithm_name}, ${storeName}, ${func.step_type}</div>`;
  }

  getAlgorithmFunctionSpec(func: AlgorithmFunctionExtended): string {
    return `${func.name}__${func.algorithm_id}__${func.algorithm_store_id}`;
  }

  async handleDatabaseStepInitialized(): Promise<void> {
    // TODO get rid of this function?
    if (!this.repeatedTask || !this.function) return;
    // This function is run when the database child component is initialized,
    // but it may still be null when we get here. If it is null, we wait a bit
    // and then (recursively) try again.
    // TODO setup database step for repeating extraction task

    // TODO repeat preprocessing and filtering when backend is ready
  }

  isFormInvalid(): boolean {
    return (
      (this.availableSteps.session && this.sessionForm.invalid) ||
      (this.availableSteps.study && this.studyForm.invalid) ||
      (this.availableSteps.function && this.functionForm.invalid) ||
      (this.availableSteps.database && this.databaseForm.invalid) ||
      (this.availableSteps.dataframe && this.dataframeForm.invalid) ||
      (this.availableSteps.parameter && this.parameterForm.invalid)
    );
  }

  async handleSubmit(): Promise<void> {
    if (this.isSubmitting) return;
    if (this.isFormInvalid()) {
      return;
    }

    this.isSubmitting = true;

    try {
      await this.submitTask();
    } catch (error) {
      this.isSubmitting = false;
    }
  }

  async submitTask(): Promise<void> {
    // setup input for task. Parse string to JSON if needed
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (!this.function) return;
    const kwargs: any = {};
    this.function.arguments.forEach((arg) => {
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
      name: this.functionForm.controls.taskName.value,
      description: this.functionForm.controls.description.value,
      image: image,
      method: this.function.name,
      session_id: Number.parseInt(this.sessionForm.controls.sessionID.value),
      collaboration_id: this.collaboration?.id || -1,
      database: this.databaseForm.controls.database.value,
      store_id: this.algorithm?.algorithm_store_id || -1,
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

    if (this.shouldShowDatabaseStep) {
      formCreateOutput.database = this.databaseForm.controls.database.value;
    }

    // TODO get this to work for algorithms that use multiple dataframes
    if (this.shouldShowDataframeStep) {
      const ids = this.dataframeForm.controls.dataframeId.value;
      formCreateOutput.dataframes = [
        (Array.isArray(ids) ? ids : [ids]).map(id => ({
          dataframe_id: id,
          type: TaskDatabaseType.Dataframe
        }))
      ];
    }

    this.onSubmit.next(formCreateOutput);
  }

  handleCancel(): void {
    this.onCancel.emit();
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

  shouldShowParameterBooleanInput(argument: Argument): boolean {
    return argument.type === this.argumentType.Boolean;
  }

  shouldShowParameterJsonInput(argument: Argument): boolean {
    return argument.type === this.argumentType.Json;
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

  isFederatedStep(stepType: AlgorithmStepType): boolean {
    return stepType !== AlgorithmStepType.CentralCompute;
  }

  containsColumnArguments(): boolean {
    return this.function?.arguments.some((arg) => arg.type === this.argumentType.Column) || false;
  }

  shouldShowColumnDropdownForAnyArg(): boolean {
    return this.containsColumnArguments();
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

  isDataExtractionStep(): boolean {
    return this.allowedTaskTypes?.includes(AlgorithmStepType.DataExtraction) || false;
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

  isFirstStep(step: AvailableStepsEnum): boolean {
    if (step === AvailableStepsEnum.Study) {
      return !this.availableSteps.session;
    } else if (step === AvailableStepsEnum.Function) {
      return !this.availableSteps.study && !this.availableSteps.session;
    } else if (step === AvailableStepsEnum.Session) {
      return true;
    } else {
      return false;
    }
  }

  isLastStep(step: AvailableStepsEnum): boolean {
    if (step === AvailableStepsEnum.Dataframe) {
      return !this.availableSteps.parameter;
    } else if (step === AvailableStepsEnum.Database) {
      return !this.availableSteps.parameter && !this.availableSteps.dataframe;
    } else if (step === AvailableStepsEnum.Function) {
      return !this.availableSteps.parameter && !this.availableSteps.dataframe && !this.availableSteps.database;
    } else if (step === AvailableStepsEnum.Parameter) {
      return true;
    } else {
      return false;
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
        return store_name;
      }
    }
    return '';
  }

  getDisplayName(obj: AlgorithmFunction | Argument): string {
    return obj.display_name && obj.display_name != '' ? obj.display_name : obj.name;
  }

  nodeConfigContainsDatabases(): boolean {
    return this.node?.config.find((_) => _.key === 'database_labels') !== undefined;
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
    this.sessions = await this.sessionService.getSessions();
    const algorithmsObj = await this.algorithmService.getAlgorithms();
    this.algorithms = algorithmsObj;
    this.functions = algorithmsObj.flatMap((curAlgorithm) => {
      return curAlgorithm.functions
        .filter((func) => func.standalone)
        .filter((func) => (this.allowedTaskTypes ? this.allowedTaskTypes.includes(func.step_type) : true))
        .map((func) => {
          return {
            ...func,
            algorithm_id: curAlgorithm.id,
            algorithm_name: curAlgorithm.name,
            algorithm_store_id: curAlgorithm.algorithm_store_id
          };
        });
    });
    this.filteredFunctions = this.functions;
    this.node = await this.getOnlineNode();
    this.availableDatabases = getDatabasesFromNode(this.node);

    this.sessionForm.controls['sessionID'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (sessionID) => {
      this.handleSessionChange(sessionID);
    });

    if (this.sessionId) {
      this.sessionForm.controls['sessionID'].setValue(this.sessionId);
    }

    // set default for study step: full collaboration (this is not visible but required
    // if there are no studies defined to have a valid form)
    this.studyForm.controls['studyOrCollabID'].setValue(StudyOrCollab.Collaboration + this.collaboration?.id.toString());
    this.updateStudyFormValidation();
    this.setOrganizations();

    this.studyForm.controls['studyOrCollabID'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (studyID) => {
      if (studyID.startsWith(StudyOrCollab.Study)) {
        this.handleStudyChange(Number(studyID.substring(StudyOrCollab.Study.length)));
      }
      if (studyID) this.isStudyCompleted = true;
    });

    this.functionForm.controls.algorithmFunctionSpec.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (algorithmFunctionSpec) => {
        const [functionName, algorithmID, algorithmStoreID] = algorithmFunctionSpec.split('__');
        this.handleFunctionChange(String(functionName), Number(algorithmID), Number(algorithmStoreID));
      });

    // set columns if dataframe is already set (for preprocessing tasks)
    if (this.dataframe) {
      this.setColumns(this.dataframe);
    }
    // set columns if dataframe is selected
    this.dataframeForm.controls['dataframeId'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (dataframeID) => {
      this.columns = [];
      let dataframe = null;
      if (Array.isArray(dataframeID) && dataframeID.length > 0) {
        // For multi-select, use the first selected dataframe to get columns
        dataframe = this.dataframes.find((_) => _.id === Number(dataframeID[0]));
      } else if (dataframeID) {
        // For single select
        dataframe = this.dataframes.find((_) => _.id === Number(dataframeID));
      }
      if (dataframe) {
        this.setColumns(dataframe);
      }
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

  setColumns(dataframe: Dataframe) {
    this.columns = dataframe.columns.map((col) => col.name);
  }

  private async handleSessionChange(sessionID: string): Promise<void> {
    this.session = this.sessions?.find((session) => session.id === Number(sessionID)) || null;
    this.studyForm.controls.studyOrCollabID.reset();
    this.isStudyCompleted = false;
    if (this.session) {
      if (this.session.study) {
        this.studyForm.get('studyOrCollabID')?.disable();
        this.studyForm.controls['studyOrCollabID'].setValue(StudyOrCollab.Study + this.session.study.id.toString());
        this.handleStudyChange(this.session.study.id);
      } else if (this.shouldShowStudyStep) {
        this.studyForm.get('studyOrCollabID')?.enable();
      }
      this.dataframes = await this.sessionService.getDataframes(this.session.id);
    }
    this.updateStudyFormValidation();
    this.clearFunctionStep();
    this.clearDatabaseStep();
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
    this.clearParameterStep();

    //Get selected algorithm
    this.algorithm = this.algorithms.find((_) => _.id === algorithmID && _.algorithm_store_id == algoStoreID) || null;
  }

  private handleFunctionChange(functionName: string, algorithmID: number, algoStoreID: number): void {
    //Clear form
    this.clearFunctionStep(); //Also clear function step, so user needs to reselect organization
    this.clearDatabaseStep();
    this.clearParameterStep();

    //Get selected function
    this.algorithm = this.algorithms.find((_) => _.id === algorithmID && _.algorithm_store_id == algoStoreID) || null;
    // Get selected function
    const selectedFunction =
      this.functions.find((_) => _.name === functionName && _.algorithm_id == algorithmID && _.algorithm_store_id == algoStoreID) || null;

    if (selectedFunction) {
      // Add form controls for parameters for selected function
      addParameterFormControlsForFunction(selectedFunction, this.parameterForm);

      // If it's a federated step, select all organizations
      if (this.isFederatedStep(selectedFunction.step_type)) {
        this.functionForm.patchValue({
          organizationIDs: this.organizations.map((org) => org.id.toString())
        });
      }
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

  // TODO this function might be removed
  private clearDatabaseStep(): void {}

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

  private updateStudyFormValidation(): void {
    const studyOrCollabControl = this.studyForm.get('studyOrCollabID');
    if (this.shouldShowStudyStep) {
      studyOrCollabControl?.setValidators(Validators.required);
    } else {
      studyOrCollabControl?.clearValidators();
    }
    studyOrCollabControl?.updateValueAndValidity();
  }

  isFirstDatabaseMultiple(): boolean {
    return this.function?.databases?.[0] ? this.function.databases[0].multiple || false : false;
  }

  hasColumnListWithMultipleDataframes(): boolean {
    if (!this.isFirstDatabaseMultiple()) return false;
    return this.function?.arguments?.some((arg: Argument) => arg.type === ArgumentType.ColumnList) || false;
  }

}
