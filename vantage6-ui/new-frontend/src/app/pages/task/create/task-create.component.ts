import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm, ArgumentType, BaseAlgorithm, AlgorithmFunction, Select } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Subject, takeUntil } from 'rxjs';
import { BaseNode } from 'src/app/models/api/node.model';
import { CreateTask, CreateTaskInput, TaskDatabase } from 'src/app/models/api/task.models';
import { TaskService } from 'src/app/services/task.service';
import { routePaths } from 'src/app/routes';
import { Router } from '@angular/router';
import { PreprocessingStepComponent } from './steps/preprocessing-step/preprocessing-step.component';
import { addParameterFormControlsForFunction } from '../task.helper';
import { DatabaseStepComponent } from './steps/database-step/database-step.component';

@Component({
  selector: 'app-task-create',
  templateUrl: './task-create.component.html',
  styleUrls: ['./task-create.component.scss']
})
export class TaskCreateComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @ViewChild(PreprocessingStepComponent)
  preprocessingStep?: PreprocessingStepComponent;
  @ViewChild(FilterStepComponent)
  filterStep?: FilterStepComponent;

  @ViewChild(DatabaseStepComponent)
  databaseStepComponent?: DatabaseStepComponent;

  destroy$ = new Subject();
  routes = routePaths;
  argumentType = ArgumentType;

  algorithms: BaseAlgorithm[] = [];
  algorithm: Algorithm | null = null;
  function: AlgorithmFunction | null = null;
  node: BaseNode | null = null;
  columns: string[] = [];
  isLoading: boolean = true;
  isLoadingColumns: boolean = false;

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

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private algorithmService: AlgorithmService,
    private taskService: TaskService,
    public chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit(): Promise<void> {
    this.initData();

    this.packageForm.controls.algorithmID.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (algorithmID) => {
      this.handleAlgorithmChange(algorithmID);
    });

    this.functionForm.controls.functionName.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (functionName) => {
      this.handleFunctionChange(functionName);
    });

    // TODO this step may not be necessary because it re-requests the
    // databases every time the organization is changed, but the databases should
    // be the same for all nodes
    this.functionForm.controls.organizationIDs.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (organizationID) => {
      this.handleOrganizationChange(organizationID);
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  get shouldShowDatabaseStep(): boolean {
    return !this.function || (!!this.function?.databases && this.function.databases.length > 0);
  }

  get shouldShowPreprocessorStep(): boolean {
    if (!this.algorithm || !this.function) return true;
    return this.algorithm.select.length > 0 && this.shouldShowDatabaseStep;
  }

  get shouldShowFilterStep(): boolean {
    if (!this.algorithm || !this.function) return true;
    return this.algorithm.filter.length > 0 && this.shouldShowDatabaseStep;
  }

  get shouldShowParameterStep(): boolean {
    return !this.function || (!!this.function && !!this.function.arguments && this.function.arguments.length > 0);
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

    const taskDatabases: TaskDatabase[] = this.getSelectedDatabases();

    const input: CreateTaskInput = {
      method: this.function?.name || '',
      kwargs: this.parameterForm.value
    };

    const createTask: CreateTask = {
      name: this.packageForm.controls.name.value,
      description: this.packageForm.controls.description.value,
      image: this.algorithm?.url || '',
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

  async handleFirstPreprocessor(): Promise<void> {
    this.isLoadingColumns = true;

    // collect data to collect columns from database
    const taskDatabases: TaskDatabase[] = this.getSelectedDatabases();
    // TODO modify when choosing database for preprocessing is implemented
    const taskDatabase = taskDatabases[0];

    // collect a node that is online
    const node = await this.getOnlineNode();
    if (!node) return; // TODO alert user that no node is online so no columns can be retrieved

    const input = { method: 'column_headers' };

    const columnRetrieveData: ColumnRetrievalInput = {
      collaboration_id: this.chosenCollaborationService.collaboration$.value?.id || -1,
      db_label: taskDatabase.label,
      organizations: [
        {
          id: node?.organization.id,
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
    console.log(columnsOrTask);
    if (columnsOrTask.columns) {
      this.columns = columnsOrTask.columns;
    } else {
      // a task has been started to retrieve the columns
      const task = await this.taskService.wait_for_results(columnsOrTask.id);
      const decodedResult: any = JSON.parse(atob(task.results?.[0].result || ''));
      this.columns = decodedResult;
    }
    this.isLoadingColumns = false;
  }

  private async initData(): Promise<void> {
    this.algorithms = await this.algorithmService.getAlgorithms();
    this.isLoading = false;
  }

  private async handleAlgorithmChange(algorithmID: string): Promise<void> {
    //Clear form
    this.clearFunctionStep();
    this.clearDatabaseStep();
    this.clearPreprocessingStep();
    this.clearFilterStep();
    this.clearParameterStep();

    //Get selected algorithm
    this.algorithm = await this.algorithmService.getAlgorithm(algorithmID);
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

  private async handleOrganizationChange(organizationID: string | string[]): Promise<void> {
    //Clear form
    this.clearDatabaseStep();
    this.node = null;

    //Get organization id, from array or string
    let id: string = organizationID.toString();
    if (Array.isArray(organizationID) && organizationID.length > 0) {
      id = organizationID[0];
    }

    //TODO: What should happen for multiple selected organizations
    // TODO if selected node is offline, try to get databases from node that is online
    //Get node
    if (id) {
      //Get all nodes for chosen collaboration
      const nodes = await this.getNodes();
      //Filter node for chosen organization
      this.node = nodes.find((_) => _.organization.id === Number.parseInt(id)) || null;
    }
  }

  private async getOnlineNode(): Promise<BaseNode | null> {
    //Get all nodes for chosen collaboration
    const nodes = await this.getNodes();

    //Find a random node that is online
    return nodes?.find((_) => _.status === 'online') || null;
  }

  private async getNodes(): Promise<BaseNode[] | null> {
    return await this.chosenCollaborationService.getNodes();
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

  private clearParameterStep(): void {
    Object.keys(this.parameterForm.controls).forEach((control) => {
      this.parameterForm.removeControl(control);
    });
  }

  private clearPreprocessingStep(): void {
    this.preprocessingStep?.clear();
    this.columns = [];
  }
}
