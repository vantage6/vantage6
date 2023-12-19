import { Component, HostBinding, OnInit, ViewChild } from '@angular/core';
import { TemplateTask } from 'src/app/models/api/templateTask.models';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm, AlgorithmFunction, ArgumentType, FunctionType } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { FormBuilder, FormControl, Validators } from '@angular/forms';
import { addParameterFormControlsForFunction, getTaskDatabaseFromForm } from '../../task/task.helper';
import { BaseNode } from 'src/app/models/api/node.model';
import { Subject, takeUntil } from 'rxjs';
import { DatabaseStepComponent } from '../../task/create/steps/database-step/database-step.component';
import { CreateTask, CreateTaskInput, TaskDatabase } from 'src/app/models/api/task.models';
import { routePaths } from 'src/app/routes';
import { TaskService } from 'src/app/services/task.service';
import { Router } from '@angular/router';
import { MatSelectChange } from '@angular/material/select';
import { SnackbarService } from 'src/app/services/snackbar.service';
import { NodeService } from 'src/app/services/node.service';

@Component({
  selector: 'app-template-task-create',
  templateUrl: './template-task-create.component.html',
  styleUrls: ['./template-task-create.component.scss']
})
export class TemplateTaskCreateComponent implements OnInit {
  @HostBinding('class') class = 'card-container';

  @ViewChild(DatabaseStepComponent)
  databaseStepComponent?: DatabaseStepComponent;

  argumentType = ArgumentType;
  functionType = FunctionType;
  destroy$ = new Subject();

  isLoadingTaskData: boolean = false;
  templateTasks: TemplateTask[] = [];
  templateTask: TemplateTask | null = null;
  algorithm: Algorithm | null = null;
  function: AlgorithmFunction | null = null;
  node: BaseNode | null = null;

  templateID = this.fb.nonNullable.control('', [Validators.required]);
  packageForm = this.fb.nonNullable.group({});
  databaseForm = this.fb.nonNullable.group({});
  parameterForm = this.fb.nonNullable.group({});

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private algorithmService: AlgorithmService,
    private taskService: TaskService,
    private nodeService: NodeService,
    private snackBarService: SnackbarService,
    public chosenCollaborationService: ChosenCollaborationService
  ) {}

  get isFormValid(): boolean {
    return (
      this.packageForm.invalid ||
      (this.shouldShowDatabaseStep && this.databaseForm.invalid) ||
      (this.shouldShowParameterStep && this.parameterForm.invalid)
    );
  }

  get shouldShowDatabaseStep(): boolean {
    if (this.templateTask?.fixed?.databases) {
      //TODO: handle preselected database with customizable sheet/query
      return false;
    }
    return !!this.function?.databases && this.function.databases.length >= 1;
  }

  get shouldShowParameterStep(): boolean {
    if (this.templateTask?.fixed?.arguments) {
      //TODO: handle fixed and variable arguments
      return false;
    }

    return !!this.function && !!this.function.arguments && this.function.arguments.length > 0;
  }

  async ngOnInit(): Promise<void> {
    await this.initData();
  }

  organizationsToDisplay(): string {
    const names: string[] = [];
    this.templateTask?.fixed?.organizations?.forEach((organizationID) => {
      const organization = this.chosenCollaborationService.collaboration$
        .getValue()
        ?.organizations.find((_) => _.id === Number.parseInt(organizationID));
      if (organization) {
        names.push(organization.name);
      }
    });
    return names.join(', ');
  }

  async handleTemplateChange(event: MatSelectChange): Promise<void> {
    this.isLoadingTaskData = true;
    this.clearForm();

    this.templateTask = this.templateTasks[event.value] || null;

    const algorithms = await this.algorithmService.getAlgorithms();
    const baseAlgorithm = algorithms.find((_) => _.image === this.templateTask?.image);
    if (baseAlgorithm) {
      this.algorithm = await this.algorithmService.getAlgorithm(baseAlgorithm?.id.toString() || '');
    } else {
      this.snackBarService.showMessage('Algorithm not found');
      return;
    }

    if (this.algorithm) {
      this.function = this.algorithm.functions.find((_) => _.name === this.templateTask?.function) || null;
    }

    if (this.function) {
      if (this.templateTask?.fixed?.arguments) {
        this.templateTask.fixed.arguments.forEach((fixedArgument) => {
          this.parameterForm.addControl(fixedArgument.name, new FormControl(fixedArgument.value));
        });
      } else {
        addParameterFormControlsForFunction(this.function, this.parameterForm);
      }
    } else {
      this.snackBarService.showMessage('Function not found');
      return;
    }

    this.templateTask.variable?.forEach((variable) => {
      if (typeof variable === 'string') {
        if (variable === 'name') {
          this.packageForm.addControl('name', new FormControl('', [Validators.required]));
        } else if (variable === 'description') {
          this.packageForm.addControl('description', new FormControl(''));
        } else if (variable === 'organizations') {
          this.packageForm.addControl('organizationIDs', new FormControl('', [Validators.required]));
          this.packageForm
            .get('organizationIDs')
            ?.valueChanges.pipe(takeUntil(this.destroy$))
            .subscribe(async (organizationID) => {
              this.handleOrganizationChange(organizationID);
            });
        }
      }
    });

    if (this.templateTask.fixed?.organizations) {
      this.handleOrganizationChange(this.templateTask.fixed.organizations);
    }
    this.isLoadingTaskData = false;
  }

  async handleSubmit(): Promise<void> {
    if (this.isFormValid) {
      return;
    }

    let selectedOrganizations: string[] = [];
    const organizationIDsControl = this.packageForm.get('organizationIDs');
    if (this.templateTask?.fixed?.organizations) {
      selectedOrganizations = this.templateTask?.fixed.organizations;
    } else if (organizationIDsControl) {
      selectedOrganizations = Array.isArray(organizationIDsControl.value) ? organizationIDsControl.value : [organizationIDsControl.value];
    }

    let taskDatabases: TaskDatabase[] = [];
    if (this.templateTask?.fixed?.databases) {
      this.templateTask.fixed.databases.forEach((fixedDatabase) => {
        const taskDatabase: TaskDatabase = { label: fixedDatabase.name, query: fixedDatabase.query, sheet: fixedDatabase.sheet };
        taskDatabases.push(taskDatabase);
      });
    } else {
      taskDatabases = getTaskDatabaseFromForm(this.function, this.databaseForm);
    }

    const input: CreateTaskInput = {
      method: this.function?.name || '',
      kwargs: this.parameterForm.value
    };

    const createTask: CreateTask = {
      name: this.templateTask?.fixed?.name ? this.templateTask.fixed.name : this.packageForm.get('name')?.value || '',
      description: this.templateTask?.fixed?.description
        ? this.templateTask.fixed.description
        : this.packageForm.get('description')?.value || '',
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

  private async initData(): Promise<void> {
    this.templateTasks = await this.taskService.getTemplateTasks();
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
    //Get node
    if (id) {
      //Get all nodes for chosen collaboration
      const nodes = await this.nodeService.getNodes({
        collaboration_id: this.chosenCollaborationService.collaboration$.value?.id.toString() || ''
      });
      //Filter node for chosen organization
      this.node = nodes.find((_) => _.organization.id === Number.parseInt(id)) || null;
    }
  }

  private clearForm(): void {
    this.templateTask = null;
    this.algorithm = null;
    this.function = null;
    this.node = null;
    this.packageForm = this.fb.nonNullable.group({});
    this.clearDatabaseStep();
    this.parameterForm = this.fb.nonNullable.group({});
  }

  private clearDatabaseStep(): void {
    this.databaseStepComponent?.reset();
  }
}
