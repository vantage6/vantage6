import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { BaseSession } from '../../../../../models/api/session.models';
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
    AlertWithButtonComponent
  ],
  standalone: true
})
export class SessionStepComponent implements OnInit, OnDestroy {
  @Input() formGroup!: FormGroup;
  @Input() allowedTaskTypes?: AlgorithmStepType[];
  @Input() dataframes: any[] = [];
  @Input() hasLoadedDataframes = false;
  @Input() session: BaseSession | null = null;

  @Output() sessionsLoaded = new EventEmitter<BaseSession[]>();

  sessions: BaseSession[] = [];

  readonly routes = routePaths;
  readonly algorithmStepType = AlgorithmStepType;

  private destroy$ = new Subject<void>();

  constructor(
    private sessionService: SessionService,
    private chosenCollaborationService: ChosenCollaborationService,
    private changesInCreateTaskService: ChangesInCreateTaskService
  ) {}

  ngOnInit(): void {
    this.loadSessions();
    this.setupFormListeners();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private async loadSessions(): Promise<void> {
    try {
      const collaboration = this.chosenCollaborationService.collaboration$.value;
      if (collaboration) {
        this.sessions = await this.sessionService.getSessions();
        this.sessionsLoaded.emit(this.sessions);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
    }
  }

  private setupFormListeners(): void {
    this.formGroup.controls['sessionID'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (sessionId: string) => {
      await this.onSessionSelected(sessionId);
    });
  }

  async onSessionSelected(sessionId: string): Promise<void> {
    const session = this.sessions.find((s) => s.id === Number(sessionId));
    this.changesInCreateTaskService.emitSessionChange(session || null);
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
