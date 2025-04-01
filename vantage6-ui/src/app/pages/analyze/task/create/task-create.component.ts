import { Component, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { routePaths } from 'src/app/routes';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { AvailableSteps, FormCreateOutput } from 'src/app/models/forms/create-form.model';
import { TaskService } from 'src/app/services/task.service';
import { CreateTask } from 'src/app/models/api/task.models';
import { CreateAnalysisFormComponent } from 'src/app/components/forms/compute-form/create-analysis-form.component';
import { AlgorithmStepType } from 'src/app/models/api/session.models';

@Component({
  selector: 'app-task-create',
  templateUrl: './task-create.component.html',
  styleUrls: ['../../../../components/forms/compute-form/create-analysis-form.component.scss'],
  encapsulation: ViewEncapsulation.None,
  imports: [ReactiveFormsModule, TranslateModule, CreateAnalysisFormComponent]
})
export class TaskCreateComponent implements OnInit, OnDestroy {
  title: string = '';
  sessionId: string = '';
  algorithmStepType = AlgorithmStepType;

  destroy$ = new Subject();

  // TODO(BART/RIAN) RIAN: Check if all available steps are implemented in the template for conditional form components.
  availableSteps: AvailableSteps = {
    session: true,
    study: true,
    function: true,
    database: false,
    dataframe: true,
    parameter: true
  };

  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute,
    public chosenCollaborationService: ChosenCollaborationService,
    public taskService: TaskService,
    private translateService: TranslateService
  ) {}

  async ngOnInit(): Promise<void> {
    this.title = this.translateService.instant('task-create.title');

    this.activatedRoute.params.pipe(takeUntil(this.destroy$)).subscribe(async (params) => {
      this.sessionId = params['sessionId'];
    });
  }

  async onSubmitHandler(formOutput: FormCreateOutput): Promise<void> {
    const newDataframe: CreateTask = {
      name: formOutput.name,
      description: formOutput.description || '-',
      image: formOutput.image,
      method: formOutput.method,
      session_id: formOutput.session_id,
      // TODO I don't like passing -1 here, needs to be fixed
      collaboration_id: formOutput.collaboration_id || -1,
      organizations: formOutput.organizations,
      store_id: formOutput.store_id,
      server_url: formOutput.server_url,
      databases: formOutput?.dataframes || []
    };
    const newTask = await this.taskService.createTask(newDataframe);
    if (newTask) {
      this.router.navigate([routePaths.task, newTask.id]);
    }
  }

  onCancelHandler(): void {
    this.router.navigate(this.sessionId ? [routePaths.session, this.sessionId] : [routePaths.tasks]);
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }
}
