import { Component, OnInit, ViewChild } from '@angular/core';
import { mockDataAllTemplateTask } from './mock';
import { TemplateTask } from 'src/app/models/api/templateTask.models';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm, ArgumentType, Function } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { FormBuilder, Validators } from '@angular/forms';
import { addParameterFormControlsForFunction } from '../../task/task.helper';
import { BaseNode } from 'src/app/models/api/node.model';
import { Subject, takeUntil } from 'rxjs';
import { DatabaseStepComponent } from '../../task/create/steps/database-step/database-step.component';

@Component({
  selector: 'app-template-task-create',
  templateUrl: './template-task-create.component.html',
  styleUrls: ['./template-task-create.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class TemplateTaskCreateComponent implements OnInit {
  @ViewChild(DatabaseStepComponent)
  databaseStepComponent?: DatabaseStepComponent;

  argumentType = ArgumentType;
  destroy$ = new Subject();

  isLoading: boolean = true;
  templateTask: TemplateTask | null = null;
  algorithm: Algorithm | null = null;
  function: Function | null = null;
  node: BaseNode | null = null;

  packageForm = this.fb.nonNullable.group({});
  databaseForm = this.fb.nonNullable.group({});
  parameterForm = this.fb.nonNullable.group({});

  constructor(
    private fb: FormBuilder,
    private algorithmService: AlgorithmService,
    public chosenCollaborationService: ChosenCollaborationService
  ) {}

  get shouldShowDatabaseStep(): boolean {
    if (this.templateTask?.fixed.databases) {
      //TODO: handle preselected database with customizable sheet/query
      return false;
    }
    return !!this.function?.databases && this.function.databases.length >= 1;
  }

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.isLoading = false;
  }

  organizationsToDisplay(): string {
    const names: string[] = [];
    this.templateTask?.fixed.organizations?.forEach((organizationID) => {
      const organization = this.chosenCollaborationService.collaboration$
        .getValue()
        ?.organizations.find((_) => _.id === Number.parseInt(organizationID));
      if (organization) {
        names.push(organization.name);
      }
    });
    return names.join(', ');
  }

  private async initData(): Promise<void> {
    this.templateTask = mockDataAllTemplateTask;

    const algorithms = await this.algorithmService.getAlgorithms();
    const baseAlgorithm = algorithms.find((_) => _.url === this.templateTask?.image);
    if (baseAlgorithm) {
      this.algorithm = await this.algorithmService.getAlgorithm(baseAlgorithm?.id.toString() || '');
    } else {
      //TODO: Add error handling with toast
      throw new Error('Algorithm not found');
    }

    if (this.algorithm) {
      this.function = this.algorithm.functions.find((_) => _.name === this.templateTask?.function) || null;
    }

    if (this.function) {
      addParameterFormControlsForFunction(this.function, this.parameterForm);
    } else {
      //TODO: Add error handling with toast
      throw new Error('Function not found');
    }

    this.templateTask.variable.forEach((variable) => {
      if (typeof variable === 'string') {
        if (variable === 'name') {
          this.packageForm.addControl('name', this.fb.nonNullable.control(''));
        } else if (variable === 'description') {
          this.packageForm.addControl('description', this.fb.nonNullable.control(''));
        } else if (variable === 'organizations') {
          this.packageForm.addControl('organizationIDs', this.fb.nonNullable.control('', [Validators.required]));
          this.packageForm
            .get('organizationIDs')
            ?.valueChanges.pipe(takeUntil(this.destroy$))
            .subscribe(async (organizationID) => {
              this.handleOrganizationChange(organizationID);
            });
        }
      }
    });

    if (this.templateTask.fixed.organizations) {
      this.handleOrganizationChange(this.templateTask.fixed.organizations);
    }
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
      const nodes = await this.chosenCollaborationService.getNodes();
      //Filter node for chosen organization
      this.node = nodes.find((_) => _.organization.id === Number.parseInt(id)) || null;
    }
  }

  private clearDatabaseStep(): void {
    this.databaseStepComponent?.reset();
  }
}
