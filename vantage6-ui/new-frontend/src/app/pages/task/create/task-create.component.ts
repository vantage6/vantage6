import { AfterViewInit, Component, HostBinding, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm, ArgumentType, AlgorithmFunction, Argument, FunctionType } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { BaseNode, NodeStatus } from 'src/app/models/api/node.model';
import { ColumnRetrievalInput, CreateTask, CreateTaskInput, Task, TaskDatabase } from 'src/app/models/api/task.models';
import { TaskService } from 'src/app/services/task.service';
import { routePaths } from 'src/app/routes';
import { Router } from '@angular/router';
import { PreprocessingStepComponent } from './steps/preprocessing-step/preprocessing-step.component';
import { addParameterFormControlsForFunction, getTaskDatabaseFromForm } from '../task.helper';
import { DatabaseStepComponent } from './steps/database-step/database-step.component';
import { FilterStepComponent } from './steps/filter-step/filter-step.component';
import { NodeService } from 'src/app/services/node.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { MatStepper } from '@angular/material/stepper';

@Component({
  selector: 'app-task-create',
  templateUrl: './task-create.component.html',
  styleUrls: ['./task-create.component.scss']
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

  algorithms: Algorithm[] = [];
  algorithm: Algorithm | null = null;
  function: AlgorithmFunction | null = null;
  node: BaseNode | null = null;
  columns: string[] = [];
  isLoading: boolean = true;
  isLoadingColumns: boolean = false;
  isTaskRepeat: boolean = false;
  isDataInitialized: boolean = false;
  repeatedTask: Task | null = null;

  packageForm = this.fb.nonNullable.group({
    algorithmID: ['', Validators.required],
    name: ['', Validators.required],
    description: ''
  });
  functionForm = this.fb.nonNullable.group({
    functionName: ['', Validators.required],
    organizationIDs: ['', Validators.required]
  });
  databaseForm = this.fb.nonNullable.group({});
  preprocessingForm = this.fb.array([]);
  filterForm = this.fb.array([]);
  parameterForm = this.fb.nonNullable.group({});

  private nodeStatusUpdateSubscription?: Subscription;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private algorithmService: AlgorithmService,
    private taskService: TaskService,
    private nodeService: NodeService,
    public chosenCollaborationService: ChosenCollaborationService,
    private socketioConnectService: SocketioConnectService
  ) {}

  async ngOnInit(): Promise<void> {
    this.isTaskRepeat = this.router.url.startsWith(routePaths.taskCreateRepeat);
    await this.initData();

    this.packageForm.controls.algorithmID.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (algorithmID) => {
      this.handleAlgorithmChange(Number(algorithmID));
    });

    this.functionForm.controls.functionName.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (functionName) => {
      this.handleFunctionChange(functionName);
    });

    this.databaseForm.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (_) => {
      this.handleDatabaseChange();
    });

    this.nodeStatusUpdateSubscription = this.socketioConnectService
      .getNodeStatusUpdates()
      .subscribe((nodeStatusUpdate: NodeOnlineStatusMsg | null) => {
        if (nodeStatusUpdate) this.onNodeStatusUpdate(nodeStatusUpdate);
      });
  }

  async ngAfterViewInit(): Promise<void> {
    if (this.isTaskRepeat) {
      this.isLoading = true;
      const taskID = this.router.url.split('/')[4];
      await this.setupRepeatTask(taskID);
      this.isLoading = false;
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
    this.nodeStatusUpdateSubscription?.unsubscribe();
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
    // TODO there are console errors when we use this routine - figure out why and resolve them
    this.repeatedTask = await this.taskService.getTask(Number(taskID));
    if (!this.repeatedTask) {
      return;
    }
    // set algorithm step
    this.packageForm.controls.name.setValue(this.repeatedTask.name);
    this.packageForm.controls.description.setValue(this.repeatedTask.description);
    const algorithm = this.algorithms.find((_) => _.image === this.repeatedTask?.image);
    if (!algorithm) return;
    this.packageForm.controls.algorithmID.setValue(algorithm.id.toString());
    await this.handleAlgorithmChange(algorithm.id);
    // set function step
    if (!this.repeatedTask.input) return;
    this.functionForm.controls.functionName.setValue(this.repeatedTask?.input?.method);
    await this.handleFunctionChange(this.repeatedTask.input?.method);
    if (!this.function) return;
    const organizationIDs = this.repeatedTask.runs.map((_) => _.organization?.id).toString();
    this.functionForm.controls.organizationIDs.setValue(organizationIDs);
    // Note: the database step is not setup here because the database child
    // component may not yet be initialized when we get here. Instead, we
    // setup the database step in the database child component when it is
    // initialized.
    // set parameter step
    for (const parameter of this.repeatedTask.input?.parameters || []) {
      this.parameterForm.get(parameter.label)?.setValue(parameter.value);
    }
    // go to last step
    // TODO this can still be NULL when we get here, then it doesn't work
    if (this.myStepper?._steps) {
      for (let idx = 0; idx < this.myStepper?._steps.length || 0; idx++) {
        this.myStepper?.next();
      }
    }
  }

  async handleDatabaseStepInitialized(): Promise<void> {
    if (!this.repeatedTask || !this.function) return;
    // set database step for task repeat
    this.databaseStepComponent?.setDatabasesFromPreviousTask(this.repeatedTask?.databases, this.function?.databases);

    // TODO repeat preprocessing and filtering when backend is ready
  }

  async handleSubmit(): Promise<void> {
    if (
      this.packageForm.invalid ||
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
          kwargs[arg.name] = arg.type === ArgumentType.Json ? JSON.parse(value) : value;
        }
      });
    });
    const input: CreateTaskInput = {
      method: this.function?.name || '',
      kwargs: kwargs
    };

    const createTask: CreateTask = {
      name: this.packageForm.controls.name.value,
      description: this.packageForm.controls.description.value,
      image: this.algorithm?.image || '',
      collaboration_id: this.chosenCollaborationService.collaboration$.value?.id || -1,
      databases: taskDatabases,
      organizations: selectedOrganizations.map((organizationID) => {
        return { id: Number.parseInt(organizationID), input: btoa(JSON.stringify(input)) || '' };
      })
      //TODO: Add preprocessing and filtering when backend is ready
    };

    const newTask = await this.taskService.createTask(createTask);
    if (newTask) {
      this.router.navigate([routePaths.task, newTask.id]);
    }
  }

  async retrieveColumns(): Promise<void> {
    this.isLoadingColumns = true;
    if (!this.node) return;

    // collect data to collect columns from database
    const taskDatabases: TaskDatabase[] = getTaskDatabaseFromForm(this.function, this.databaseForm);
    // TODO modify when choosing database for preprocessing is implemented
    const taskDatabase = taskDatabases[0];

    const input = { method: 'column_headers' };

    const columnRetrieveData: ColumnRetrievalInput = {
      collaboration_id: this.chosenCollaborationService.collaboration$.value?.id || -1,
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
    if (taskDatabase.sheet) {
      columnRetrieveData.sheet_name = taskDatabase.sheet;
    }

    // call /column endpoint. This returns either a list of columns or a task
    // that will retrieve the columns
    // TODO handle errors (both for retrieving columns and for retrieving the task)
    // TODO enable user to exit requesting column names if it takes too long
    const columnsOrTask = await this.taskService.getColumnNames(columnRetrieveData);
    if (columnsOrTask.columns) {
      this.columns = columnsOrTask.columns;
    } else {
      // a task has been started to retrieve the columns
      const task = await this.taskService.waitForResults(columnsOrTask.id);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const decodedResult: any = JSON.parse(atob(task.results?.[0].result || ''));
      this.columns = decodedResult;
    }
    this.isLoadingColumns = false;
  }

  shouldShowColumnDropdown(argument: Argument): boolean {
    return argument.type === this.argumentType.Column && this.columns.length > 0;
  }

  shouldShowColumnDropdownForAnyArg(): boolean {
    return this.function?.arguments.some((arg) => this.shouldShowColumnDropdown(arg)) || false;
  }

  // compare function for mat-select
  compareOrganizationsForSelection(obj1: any, obj2: any): boolean {
    // The mat-select object set from typescript only has an ID set. Compare that with the ID of the
    // organization object from the collaboration
    return obj1 && obj2 && obj1.id && obj2.id && obj1.id === obj2.id;
  }

  private async initData(): Promise<void> {
    this.algorithms = await this.algorithmService.getAlgorithms();
    // TODO if node is null, alert user that no node is online so no columns and databases can be retrieved - so better not create a task
    this.node = await this.getOnlineNode();
    if (!this.isTaskRepeat) this.isLoading = false;
    this.isDataInitialized = true;
  }

  private async handleAlgorithmChange(algorithmID: number): Promise<void> {
    //Clear form
    this.clearFunctionStep();
    this.clearDatabaseStep();
    this.clearPreprocessingStep();
    this.clearFilterStep();
    this.clearParameterStep();

    //Get selected algorithm
    this.algorithm = this.algorithms.find((_) => _.id === algorithmID) || null;
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

  private async handleDatabaseChange(): Promise<void> {
    if (this.databaseForm.invalid || Object.keys(this.databaseForm.controls).length === 0) return;

    // gather data to retrieve columns - these are often required in the steps that follow
    await this.retrieveColumns();
  }

  private async getOnlineNode(): Promise<BaseNode | null> {
    //Get all nodes for chosen collaboration
    const nodes = await this.getNodes();

    //Find a random node that is online
    return nodes?.find((_) => _.status === 'online') || null;
  }

  private async getNodes(): Promise<BaseNode[] | null> {
    return await this.nodeService.getNodes({
      collaboration_id: this.chosenCollaborationService.collaboration$.value?.id.toString() || ''
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
  }
}
