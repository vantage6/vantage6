import { Component, Input, OnInit, OnDestroy } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
import { BaseSession, Dataframe } from '../../../../../models/api/session.models';
import { SessionService } from '../../../../../services/session.service';
import { ChosenCollaborationService } from '../../../../../services/chosen-collaboration.service';
import { AlgorithmStepType } from '../../../../../models/api/session.models';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import { NgIf, NgFor } from '@angular/common';
import { AlertComponent } from '../../../../alerts/alert/alert.component';
import { AlertWithButtonComponent } from '../../../../alerts/alert-with-button/alert-with-button.component';
import { routePaths } from '../../../../../routes';
import { ChangesInCreateTaskService } from 'src/app/services/changes-in-create-task.service';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-session-step',
  templateUrl: './session-step.component.html',
  styleUrls: ['./session-step.component.scss'],
  imports: [
    TranslateModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    RouterModule,
    NgIf,
    NgFor,
    AlertComponent,
    AlertWithButtonComponent,
    MatProgressSpinner
  ],
  standalone: true
})
export class SessionStepComponent implements OnInit, OnDestroy {
  @Input() formGroup!: FormGroup;
  @Input() allowedTaskTypes?: AlgorithmStepType[];
  @Input() dataframes: Dataframe[] = [];
  @Input() hasLoadedDataframes = false;
  @Input() isLoadingRepeatTask: boolean = false;

  sessions: BaseSession[] = [];
  session: BaseSession | null = null;
  isLoading: boolean = false;

  readonly routes = routePaths;
  readonly algorithmStepType = AlgorithmStepType;

  private destroy$ = new Subject<void>();
  public readonly initialized$ = new BehaviorSubject<boolean>(false);

  constructor(
    private sessionService: SessionService,
    private chosenCollaborationService: ChosenCollaborationService,
    private changesInCreateTaskService: ChangesInCreateTaskService,
    private organizationService: OrganizationService
  ) {}

  async ngOnInit(): Promise<void> {
    this.isLoading = true;
    await this.loadSessions();
    this.isLoading = false;
    this.setupFormListeners();
    this.initialized$.next(true);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private async loadSessions(): Promise<void> {
    const collaboration = this.chosenCollaborationService.collaboration$.value;
    if (collaboration) {
      this.sessions = await this.sessionService.getSessions();
    }
  }

  private setupFormListeners(): void {
    this.formGroup.controls['sessionID'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (sessionId: string) => {
      await this.onSessionSelected(sessionId);
    });
  }

  public setupRepeatTask(sessionId: string): void {
    this.formGroup.controls['sessionID'].setValue(sessionId);
    this.onSessionSelected(sessionId);
  }

  async onSessionSelected(sessionId: string): Promise<void> {
    const session = this.sessions.find((s) => s.id === Number(sessionId));
    if (!session) return;
    this.session = session;
    this.changesInCreateTaskService.emitSessionChange(session);
    if (this.session.study) {
      this.changesInCreateTaskService.emitStudyChange(this.session.study.id);
      const organizations = await this.organizationService.getOrganizations({ study_id: this.session.study.id });
      this.changesInCreateTaskService.emitOrganizationChange(organizations);
    }
  }

  get hasNoSessions(): boolean {
    return this.sessions.length < 1;
  }

  get hasSessions(): boolean {
    return this.sessions.length > 0;
  }

  get shouldShowNoDataframesAlert(): boolean {
    return this.hasLoadedDataframes && this.dataframes.length === 0 && !this.allowedTaskTypes?.includes(AlgorithmStepType.DataExtraction);
  }

  get allDataframesNotReady(): boolean {
    return this.hasLoadedDataframes && this.dataframes.length > 0 && this.dataframes.every((df) => !df.ready);
  }
}
