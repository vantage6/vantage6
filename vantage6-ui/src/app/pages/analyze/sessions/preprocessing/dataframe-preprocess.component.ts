import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { routePaths } from 'src/app/routes';
import { SessionService } from 'src/app/services/session.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { combineLatest, Subject, takeUntil } from 'rxjs';
import { StudyService } from 'src/app/services/study.service';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { AlgorithmStepType, Dataframe, DataframePreprocess, Session } from 'src/app/models/api/session.models';
import { Collaboration } from 'src/app/models/api/collaboration.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { FormCreateOutput } from 'src/app/models/forms/create-form.model';
import { TranslateService } from '@ngx-translate/core';
import { CreateAnalysisFormComponent } from 'src/app/components/forms/compute-form/create-analysis-form.component';
import { ChangesInCreateTaskService } from 'src/app/services/changes-in-create-task.service';

@Component({
  selector: 'app-dataframe-preprocess',
  templateUrl: './dataframe-preprocess.component.html',
  imports: [CreateAnalysisFormComponent]
})
export class DataframePreprocessComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  algorithmStepType = AlgorithmStepType;

  title: string = '';
  destroy$ = new Subject();

  public sessionId?: string;
  public dfId?: string;

  dataframe: Dataframe | null = null;
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
    private translateService: TranslateService,
    private changesInCreateTaskService: ChangesInCreateTaskService
  ) {}

  ngOnInit(): void {
    combineLatest([
      this.activatedRoute.params.pipe(takeUntil(this.destroy$)),
      this.chosenCollaborationService.isInitialized$.pipe(takeUntil(this.destroy$))
    ]).subscribe(([params, initialized]) => {
      this.dfId = params['dfId'];
      this.sessionId = params['sessionId'];
      if (initialized) {
        this.initData();
      }
    });
    this.changesInCreateTaskService.dataframeChange$.pipe(takeUntil(this.destroy$)).subscribe((dataframes) => {
      if (dataframes.length > 0) {
        this.dataframe = dataframes[0];
      }
    });
  }

  private async initData(): Promise<void> {
    this.collaboration = this.chosenCollaborationService.collaboration$.value;
    if (this.dfId) {
      this.dataframe = await this.sessionService.getDataframe(Number(this.dfId));
      this.title = this.translateService.instant('preprocessing.title', {
        name: this.dataframe?.name || ''
      });
    } else {
      this.title = this.translateService.instant('preprocessing.title-without-session');
    }
    if (this.sessionId) {
      this.session = await this.sessionService.getSession(Number(this.sessionId));
    }
    this.algorithms = await this.algorithmService.getAlgorithms();
    this.study_id = this.session?.study?.id ?? null;
  }

  async onSubmitHandler(formCreateOutput: FormCreateOutput): Promise<void> {
    if (!this.dataframe) return;
    const dataframeInput: DataframePreprocess = {
      dataframe_id: this.dataframe.id,
      task: {
        image: formCreateOutput.image,
        method: formCreateOutput.method,
        store_id: formCreateOutput.store_id,
        organizations: formCreateOutput.organizations
      }
    };
    const newDataframe = await this.sessionService.createPreprocessingTask(this.dataframe.id, dataframeInput);
    if (newDataframe) {
      this.router.navigate([routePaths.task, newDataframe.last_session_task.id]);
    }
  }

  onCancelHandler(): void {
    this.router.navigate([routePaths.sessionDataframe, this.dfId]);
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }
}
