import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { routePaths } from 'src/app/routes';
import { SessionService } from 'src/app/services/session.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Subject, takeUntil } from 'rxjs';
import { StudyService } from 'src/app/services/study.service';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStepType, CreateDataframe, Session } from 'src/app/models/api/session.models';
import { Collaboration } from 'src/app/models/api/collaboration.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { AvailableSteps, FormCreateOutput } from 'src/app/models/forms/create-form.model';
import { TranslateService } from '@ngx-translate/core';
import { CreateAnalysisFormComponent } from 'src/app/components/forms/compute-form/create-analysis-form.component';

@Component({
  selector: 'app-dataframe-create',
  templateUrl: './dataframe-create.component.html',
  imports: [CreateAnalysisFormComponent]
})
export class DataframeCreateComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  algorithmStepType = AlgorithmStepType;

  title: string = '';

  destroy$ = new Subject();

  public sessionId?: string;

  session: Session | null = null;
  study_id: number | null = null;
  collaboration?: Collaboration | null = null;
  algorithms: Algorithm[] = [];

  constructor(
    public sessionService: SessionService,
    public studyService: StudyService,
    public chosenCollaborationService: ChosenCollaborationService,
    public organizationService: OrganizationService,
    private algorithmService: AlgorithmService,
    private router: Router,
    private activatedRoute: ActivatedRoute,
    private translateService: TranslateService
  ) {}

  ngOnInit(): void {
    this.title = this.translateService.instant('session.dataframes.add');
    this.activatedRoute.params.pipe(takeUntil(this.destroy$)).subscribe(async (params) => {
      this.sessionId = params['sessionId'];
    });

    this.chosenCollaborationService.isInitialized$.pipe(takeUntil(this.destroy$)).subscribe((initialized) => {
      if (initialized) {
        this.initData();
      }
    });
  }

  private async initData(): Promise<void> {
    this.collaboration = this.chosenCollaborationService.collaboration$.value;

    // Only try to get session if sessionId is provided
    if (this.sessionId) {
      this.session = await this.sessionService.getSession(Number(this.sessionId));
      this.study_id = this.session?.study?.id ?? null;
    }

    this.algorithms = await this.algorithmService.getAlgorithms();
  }

  async onSubmitHandler(formCreateOutput: FormCreateOutput): Promise<void> {
    let session_id: number = Number(formCreateOutput.session_id);
    const dataframeInput: CreateDataframe = {
      name: formCreateOutput.name,
      label: formCreateOutput.database || '',
      task: {
        image: formCreateOutput.image,
        method: formCreateOutput.method,
        store_id: formCreateOutput.store_id,
        organizations: formCreateOutput.organizations
      }
    };
    const newDataframe = await this.sessionService.createDataframe(session_id, dataframeInput);
    if (newDataframe) {
      this.router.navigate([routePaths.task, newDataframe.last_session_task.id]);
    }
  }

  onCancelHandler(): void {
    if (this.sessionId) {
      this.router.navigate([routePaths.session, this.sessionId]);
    } else {
      this.router.navigate([routePaths.sessions]);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }
}
