import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { routePaths } from 'src/app/routes';
import { SessionService } from 'src/app/services/session.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Subject, takeUntil } from 'rxjs';
import { StudyService } from 'src/app/services/study.service';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { Session } from 'src/app/models/api/session.models';
import { Collaboration } from 'src/app/models/api/collaboration.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { AvailableSteps, FormCreateOutput } from 'src/app/models/forms/create-form.model';
import { TranslateService } from '@ngx-translate/core';
import { FormCreateComponent } from 'src/app/components/forms/compute-form/create-form.component';

@Component({
  selector: 'app-dataframe-create',
  templateUrl: './dataframe-create.component.html',
  imports: [FormCreateComponent]
})
export class DataframeCreateComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';

  title: string = '';
  availableSteps: AvailableSteps = {
    session: false,
    study: false,
    function: true,
    database: true,
    dataframe: false,
    preprocessing: true,
    filter: true,
    parameter: false
  };

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
    this.session = await this.sessionService.getSession(Number(this.sessionId));
    this.algorithms = await this.algorithmService.getAlgorithms();
    this.study_id = this.session?.study?.id ?? null;
  }

  async onSubmitHandler(formCreateOutput: FormCreateOutput): Promise<void> {
    // TODO(BART/RIAN) RIAN: Change the create dataframe form input to include the required input fields.
    // TODO(BART/RIAN) RIAN: Change the create dataframe api parameters and modify the code below. Also add extra UI components to sessions / read to display the extra dataframe information.
    //
    // const newDataframe: CreateTask = {
    //   handle: formCreateOutput?.name || '',
    //   label: '#! add label info',
    //   description: '',
    //   image: formCreateOutput.image || '',
    //   session_id: Number(this.sessionId) || -1,
    //   collaboration_id: this.chosenCollaborationService.collaboration$.value?.id || -1,
    //   store_id: formCreateOutput.store_id || -1,
    //   server_url: formCreateOutput.server_url || '',
    //   databases: formCreateOutput.databases || [],
    //   organizations: formCreateOutput.organizations || []
    //   //TODO: Add preprocessing and filtering when backend is ready
    // };
    let session_id: number = Number(this.sessionId);
    const dataframeInput: any = {
      handle: formCreateOutput?.name || '',
      label: formCreateOutput?.name || '',
      //TODO(BART/RIAN) RIAN: Add component parameters for conditional 'Name', 'Label', 'Description' etc and process this in form-create.component
      // description: '',
      task: {
        image: formCreateOutput.image || '',
        organizations: formCreateOutput.organizations || []
      }
    };
    const newDataframe = await this.sessionService.createDataframe(session_id, dataframeInput);
    if (newDataframe) {
      this.router.navigate([routePaths.session, session_id]);
    }
  }

  onCancelHandler(): void {
    this.router.navigate([routePaths.session, this.sessionId]);
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }
}
