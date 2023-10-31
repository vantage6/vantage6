import { Component } from '@angular/core';
import { mockDataQualityTemplateTask } from './mock';
import { TemplateTask } from 'src/app/models/api/templateTask.models';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm, Function } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { FormBuilder, Validators } from '@angular/forms';

@Component({
  selector: 'app-template-task-create',
  templateUrl: './template-task-create.component.html',
  styleUrls: ['./template-task-create.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class TemplateTaskCreateComponent {
  isLoading: boolean = true;
  templateTask: TemplateTask | null = null;
  algorithm: Algorithm | null = null;
  function: Function | null = null;

  variableForm = this.fb.nonNullable.group({});

  constructor(
    private fb: FormBuilder,
    private algorithmService: AlgorithmService,
    public chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.isLoading = false;
  }

  private async initData(): Promise<void> {
    this.templateTask = mockDataQualityTemplateTask;

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
    } else {
      //TODO: Add error handling with toast
      throw new Error('Function not found');
    }

    this.templateTask.variable.forEach((variable) => {
      if (typeof variable === 'string') {
        if (variable === 'description') {
          this.variableForm.addControl('description', this.fb.nonNullable.control(''));
        }
        if (variable === 'organizations') {
          this.variableForm.addControl('organizationIDs', this.fb.nonNullable.control('', [Validators.required]));
        }
      }
    });
  }
}
