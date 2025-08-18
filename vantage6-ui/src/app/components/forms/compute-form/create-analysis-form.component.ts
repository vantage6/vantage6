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
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm, ArgumentType, AlgorithmFunctionExtended } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { BaseNode, NodeStatus } from 'src/app/models/api/node.model';
import { Task, TaskDatabaseType, TaskLazyProperties } from 'src/app/models/api/task.models';
import { routePaths } from 'src/app/routes';
import { Router } from '@angular/router';
import { NodeService } from 'src/app/services/node.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { MatStepper, MatStepperIcon, MatStep, MatStepLabel, MatStepperNext, MatStepperPrevious } from '@angular/material/stepper';
import { SnackbarService } from 'src/app/services/snackbar.service';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Collaboration } from 'src/app/models/api/collaboration.model';
import { StudyOrCollab } from 'src/app/models/api/study.model';
import { MAX_ATTEMPTS_RENEW_NODE, SECONDS_BETWEEN_ATTEMPTS_RENEW_NODE } from 'src/app/models/constants/wait';
import { EncryptionService } from 'src/app/services/encryption.service';
import { AlgorithmStepType, Dataframe } from 'src/app/models/api/session.models';
import { AvailableSteps, AvailableStepsEnum, FormCreateOutput } from 'src/app/models/forms/create-form.model';
import { PageHeaderComponent } from '../../page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { AlertComponent } from '../../alerts/alert/alert.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { NgIf, NgTemplateOutlet } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { getDatabasesFromNode } from 'src/app/helpers/node.helper';
import { SessionStepComponent } from './task-steps/session-step/session-step.component';
import { StudyStepComponent } from './task-steps/study-step/study-step.component';
import { FunctionStepComponent } from './task-steps/function-step/function-step.component';
import { DatabaseStepComponent } from './task-steps/database-step/database-step.component';
import { DataframeStepComponent } from './task-steps/dataframe-step/dataframe-step.component';
import { ParameterStepComponent } from './task-steps/parameter-step/parameter-step.component';
import { ChangesInCreateTaskService } from 'src/app/services/changes-in-create-task.service';
import { TaskService } from 'src/app/services/task.service';

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
    MatProgressSpinner,
    MatButton,
    TranslateModule,
    ReactiveFormsModule,
    NgIf,
    NgTemplateOutlet,
    SessionStepComponent,
    StudyStepComponent,
    FunctionStepComponent,
    DatabaseStepComponent,
    DataframeStepComponent,
    ParameterStepComponent
  ]
})
export class CreateAnalysisFormComponent implements OnInit, OnDestroy, AfterViewInit {
  @HostBinding('class') class = 'card-container';
  availableStepsEnum = AvailableStepsEnum;

  @Input() formTitle: string = '';
  @Input() sessionId?: string = '';
  @Input() allowedTaskTypes?: AlgorithmStepType[];
  @Input() preSelectedDataframes: Dataframe[] = [];

  @Output() public onSubmit: EventEmitter<FormCreateOutput> = new EventEmitter<FormCreateOutput>();
  @Output() public onCancel: EventEmitter<void> = new EventEmitter();

  @ViewChild(SessionStepComponent) private sessionStepComponent: SessionStepComponent | null = null;
  @ViewChild(StudyStepComponent) private studyStepComponent: StudyStepComponent | null = null;

  availableSteps: AvailableSteps = {
    session: false,
    study: false,
    function: false,
    database: false,
    dataframe: false,
    parameter: false
  };

  destroy$ = new Subject();
  routes = routePaths;
  argumentType = ArgumentType;
  studyOrCollab = StudyOrCollab;

  algorithms: Algorithm[] = [];
  algorithm: Algorithm | null = null;
  collaboration?: Collaboration | null = null;
  functions: AlgorithmFunctionExtended[] = [];
  function: AlgorithmFunctionExtended | null = null;
  dataframes: Dataframe[] = [];
  node: BaseNode | null = null;

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
  dataframeForm = this.fb.nonNullable.group({});
  parameterForm: FormGroup = this.fb.nonNullable.group({});

  private nodeStatusUpdateSubscription?: Subscription;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private changeDetectorRef: ChangeDetectorRef,
    private algorithmService: AlgorithmService,
    private nodeService: NodeService,
    public chosenCollaborationService: ChosenCollaborationService,
    private socketioConnectService: SocketioConnectService,
    private snackBarService: SnackbarService,
    private translateService: TranslateService,
    private encryptionService: EncryptionService,
    private changesInCreateTaskService: ChangesInCreateTaskService,
    private taskService: TaskService
  ) {}

  async ngOnInit(): Promise<void> {
    this.setAvailableTaskSteps(this.allowedTaskTypes || []);
    this.setupChangeListeners();
    this.isTaskRepeat = this.router.url.includes('/repeat/');

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
      const splitted = this.router.url.split('/');
      const taskID = splitted[splitted.length - 1];
      // Ensure the content is rendered so child components are created
      this.changeDetectorRef.detectChanges();
      await new Promise((f) => setTimeout(f, 0));
      await this.setupRepeatTask(taskID);
    }
    this.changeDetectorRef.detectChanges();
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
    this.nodeStatusUpdateSubscription?.unsubscribe();
  }

  private setupChangeListeners(): void {
    this.changesInCreateTaskService.functionAlgorithmChange$.pipe(takeUntil(this.destroy$)).subscribe((algorithm) => {
      this.algorithm = algorithm;
    });
    this.changesInCreateTaskService.functionChange$.pipe(takeUntil(this.destroy$)).subscribe((function_) => {
      this.function = function_;
    });
  }

  get shouldShowStudyStep(): boolean {
    return (this.collaboration && this.collaboration.studies.length > 0) || false;
  }

  get shouldShowDataframeStep(): boolean {
    return !!this.function?.databases && this.function.databases.length > 0 && this.preSelectedDataframes.length === 0;
  }

  get shouldShowDatabaseStep(): boolean {
    return !this.function || (!!this.function?.databases && this.function.databases.length > 0);
  }

  get shouldShowParameterStep(): boolean {
    return !this.function || (!!this.function && !!this.function.arguments && this.function.arguments.length > 0);
  }

  private setAvailableTaskSteps(allowedTaskTypes: AlgorithmStepType[]): void {
    if (allowedTaskTypes.length > 0) {
      this.availableSteps = {
        session:
          allowedTaskTypes.includes(AlgorithmStepType.FederatedCompute) ||
          allowedTaskTypes.includes(AlgorithmStepType.CentralCompute) ||
          !this.sessionId,
        study: allowedTaskTypes.includes(AlgorithmStepType.FederatedCompute) || allowedTaskTypes.includes(AlgorithmStepType.CentralCompute),
        function: true,
        database: allowedTaskTypes.includes(AlgorithmStepType.DataExtraction),
        dataframe:
          allowedTaskTypes.includes(AlgorithmStepType.FederatedCompute) ||
          allowedTaskTypes.includes(AlgorithmStepType.CentralCompute) ||
          allowedTaskTypes.includes(AlgorithmStepType.Preprocessing),
        parameter: true
      };
    }
  }

  private async waitForSubComponentReady(subComponent: any): Promise<void> {
    // Wait until the child component exists and has finished its own initialization
    while (!subComponent || !subComponent.initialized$.value) {
      await new Promise((f) => setTimeout(f, 50));
    }
  }

  async setupRepeatTask(taskID: string): Promise<void> {
    this.repeatedTask = await this.taskService.getTask(Number(taskID), [TaskLazyProperties.InitOrg]);
    if (!this.repeatedTask) {
      return;
    }
    await this.waitForSubComponentReady(this.sessionStepComponent);
    this.sessionStepComponent?.selectSessionNonInteractively(this.repeatedTask.session.id.toString());
    if (this.studyStepComponent) {
      if (this.repeatedTask.study?.id) {
        this.studyStepComponent.setStudyNonInteractively(StudyOrCollab.Study + this.repeatedTask.study.id.toString());
      } else {
        this.studyStepComponent.setStudyNonInteractively(StudyOrCollab.Collaboration + this.collaboration?.id.toString());
      }
    }
    // // set algorithm step
    // this.showWarningUniqueDFName = false;
    // if (!(this.allowedTaskTypes?.length === 1 && this.allowedTaskTypes[0] === AlgorithmStepType.DataExtraction)) {
    //   // don't set task name for data extraction tasks - it will be used as the name
    //   // of the created dataframe and that must be unique for the session
    //   this.functionForm.controls.taskName.setValue(this.repeatedTask.name);
    // } else {
    //   this.showWarningUniqueDFName = true;
    // }
    // this.functionForm.controls.description.setValue(this.repeatedTask.description);
    // this.algorithm = this.getAlgorithmFromImage(this.repeatedTask.image);
    // if (this.algorithm === null || this.algorithm?.algorithm_store_id === undefined) return;
    // // set function step
    // const func =
    //   this.functionsAllowedForSession.find(
    //     (_) =>
    //       _.name === this.repeatedTask?.method &&
    //       _.algorithm_id == this.algorithm?.id &&
    //       _.algorithm_store_id == this.algorithm?.algorithm_store_id
    //   ) || null;
    // if (!func) return;
    // this.functionForm.controls.algorithmFunctionSpec.setValue(this.getAlgorithmFunctionSpec(func));
    // await this.handleFunctionChange(this.repeatedTask.method, this.algorithm.id, this.algorithm?.algorithm_store_id);
    // if (!this.function) return;
    // const organizationIDs = this.repeatedTask.runs.map((_) => _.organization?.id?.toString() ?? '').filter((value) => value);
    // this.functionForm.controls.organizationIDs.setValue(organizationIDs);
    // // set database step
    // if (this.availableSteps.database && this.repeatedTask.databases && this.repeatedTask.databases.length > 0) {
    //   this.databaseForm.controls.database.setValue(this.repeatedTask.databases[0].label);
    // }
    // // set dataframe step
    // if (this.availableSteps.dataframe && this.repeatedTask.databases && this.repeatedTask.databases.length > 0) {
    //   this.repeatedTask.databases.forEach((db, idx) => {
    //     (this.dataframeForm.get(`dataframeId${idx}`) as any)?.setValue(db.dataframe_id?.toString() || '');
    //   });
    //   await this.handleDataframeChange(this.repeatedTask.databases.map((db) => db.dataframe_id?.toString() || ''));
    // }
    // // set parameter step
    // for (const parameter of this.repeatedTask.arguments || []) {
    //   const argument: Argument | undefined = this.function?.arguments.find((_) => _.name === parameter.label);
    //   // check if value is an object
    //   if (!argument) {
    //     // this should never happen, but fallback is simply try to fill value in
    //     this.parameterForm.get(parameter.label)?.setValue(parameter.value);
    //   } else if (argument.type === ArgumentType.Json) {
    //     this.parameterForm.get(parameter.label)?.setValue(JSON.stringify(parameter.value));
    //   } else if (
    //     argument.type === ArgumentType.FloatList ||
    //     argument.type === ArgumentType.IntegerList ||
    //     argument.type == ArgumentType.StringList
    //   ) {
    //     const controls = this.getFormArrayControls(argument);
    //     let isFirst = true;
    //     for (const value of parameter.value) {
    //       if (!isFirst) controls.push(this.getNewControlForArgumentList(argument));
    //       controls[controls.length - 1].setValue(value);
    //       isFirst = false;
    //     }
    //   } else if (argument.type === ArgumentType.Boolean) {
    //     this.parameterForm.get(parameter.label)?.setValue(parameter.value ? true : false);
    //   } else {
    //     this.parameterForm.get(parameter.label)?.setValue(parameter.value);
    //   }
    // }
  }

  isFormInvalid(): boolean {
    return (
      (this.availableSteps.session && this.sessionForm.invalid) ||
      (this.availableSteps.study && this.studyForm.invalid) ||
      (this.availableSteps.function && this.functionForm.invalid) ||
      (this.availableSteps.database && this.databaseForm.invalid) ||
      (this.availableSteps.dataframe && this.dataframeForm.invalid && this.shouldShowDataframeStep) ||
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
    // setup arguments for task. Parse string to JSON if needed
    if (!this.function) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const arguments_: any = {};
    this.function.arguments.forEach((arg) => {
      Object.keys(this.parameterForm.controls).forEach((control) => {
        if (control === arg.name) {
          const value = this.parameterForm.get(control)?.value;
          if (arg.is_frontend_only || (arg.has_default_value && value === null)) {
            return; // note that within .forEach, return is like continue
          } else if (arg.type === ArgumentType.Json) {
            arguments_[arg.name] = JSON.parse(value);
          } else if (arg.type === ArgumentType.Float || arg.type === ArgumentType.Integer) {
            arguments_[arg.name] = Number(value);
          } else if (
            arg.type === ArgumentType.FloatList ||
            arg.type === ArgumentType.IntegerList ||
            arg.type === ArgumentType.OrganizationList
          ) {
            arguments_[arg.name] = value.map((_: string) => Number(_));
          } else {
            arguments_[arg.name] = value;
          }
        }
      });
    });

    const selectedOrganizations = Array.isArray(this.functionForm.controls.organizationIDs.value)
      ? this.functionForm.controls.organizationIDs.value
      : [this.functionForm.controls.organizationIDs.value];
    // encrypt the arguments for each organization
    const argumentsPerOrg: { [key: string]: string } = {};
    const argumentsStringified = btoa(JSON.stringify(arguments_)) || '';
    for (const organizationID of selectedOrganizations) {
      const org_arguments = await this.encryptionService.encryptData(argumentsStringified, Number(organizationID));
      argumentsPerOrg[organizationID] = org_arguments;
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
          arguments: argumentsPerOrg[organizationID] || ''
        };
      })
    };

    if (this.studyForm.controls['studyOrCollabID'].value.startsWith(StudyOrCollab.Study)) {
      formCreateOutput.study_id = Number(this.studyForm.controls['studyOrCollabID'].value.substring(StudyOrCollab.Study.length));
    }

    if (this.shouldShowDatabaseStep) {
      formCreateOutput.database = this.databaseForm.controls.database.value;
    }

    if (this.shouldShowDataframeStep) {
      const dataframes: { dataframe_id: number; type: TaskDatabaseType }[][] = [];
      if (this.function?.databases) {
        this.function.databases.forEach((_, idx) => {
          const value = (this.dataframeForm.get(`dataframeId${idx}`) as any)?.value;
          if (value) {
            if (Array.isArray(value)) {
              dataframes.push(value.map((id: any) => ({ dataframe_id: Number(id), type: TaskDatabaseType.Dataframe })));
            } else {
              dataframes.push([{ dataframe_id: Number(value), type: TaskDatabaseType.Dataframe }]);
            }
          }
        });
      }
      formCreateOutput.dataframes = dataframes;
    }

    this.onSubmit.next(formCreateOutput);
  }

  handleCancel(): void {
    this.onCancel.emit();
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

  private hasParameterStep(): boolean {
    return this.availableSteps.parameter && this.function != null && this.function?.arguments.length > 0;
  }

  private hasDataframeStep(): boolean {
    return this.availableSteps.dataframe && this.function != null && this.function?.databases.length > 0;
  }

  private hasDatabaseStep(): boolean {
    return this.availableSteps.database && this.function != null && this.function?.databases.length > 0;
  }

  isLastStep(step: AvailableStepsEnum): boolean {
    if (step === AvailableStepsEnum.Dataframe) {
      return !this.hasParameterStep();
    } else if (step === AvailableStepsEnum.Database) {
      return !this.hasParameterStep() && !this.hasDataframeStep();
    } else if (step === AvailableStepsEnum.Function) {
      return !this.hasParameterStep() && !this.hasDataframeStep() && !this.hasDatabaseStep();
    } else if (step === AvailableStepsEnum.Parameter) {
      return true;
    } else {
      return false;
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

  private async initData(): Promise<void> {
    this.collaboration = this.chosenCollaborationService.collaboration$.value;
    if (!this.collaboration) return;
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
    this.node = await this.getOnlineNode();

    // set initial values for the services
    this.changesInCreateTaskService.emitOrganizationChange(this.collaboration.organizations);
    this.changesInCreateTaskService.emitNodeDatabasesChange(getDatabasesFromNode(this.node));

    this.nodeStatusUpdateSubscription = this.socketioConnectService
      .getNodeStatusUpdates()
      .subscribe((nodeStatusUpdate: NodeOnlineStatusMsg | null) => {
        if (nodeStatusUpdate) this.onNodeStatusUpdate(nodeStatusUpdate);
      });

    this.isNgInitDone = true;

    this.isDataInitialized = true;
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
