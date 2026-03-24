import { Component, HostBinding, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { routePaths } from 'src/app/routes';
import { CreateSession, Session, SessionScope } from 'src/app/models/api/session.models';
import { SessionService } from 'src/app/services/session.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { BaseStudy } from 'src/app/models/api/study.model';
import { Collaboration } from 'src/app/models/api/collaboration.model';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { NgIf, NgFor } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatSelect } from '@angular/material/select';
import { MatOption } from '@angular/material/core';
import { Subject, takeUntil } from 'rxjs';
import { StudyService } from 'src/app/services/study.service';
import { TranslateService } from '@ngx-translate/core';
import { MatInput } from '@angular/material/input';
import { getEnumKeyByValue } from 'src/app/helpers/utils.helper';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-session-create',
  templateUrl: './session-create.component.html',
  imports: [
    PageHeaderComponent,
    NgIf,
    MatCard,
    NgFor,
    MatButton,
    MatFormField,
    MatLabel,
    MatSelect,
    ReactiveFormsModule,
    MatOption,
    MatCardContent,
    MatInput,
    MatSelect,
    MatProgressSpinner,
    TranslateModule
  ]
})
export class SessionCreateComponent implements OnInit {
  @HostBinding('class') class = 'card-container';

  destroy$ = new Subject();
  isLoading = false;

  public title: string = '';
  public session?: Session;
  public scopeKeys = Object.keys(SessionScope);
  public collaboration: Collaboration | null = this.chosenCollaborationService.collaboration$.value;
  public studies: BaseStudy[] | null = this.collaboration?.studies || null;
  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    scope: ['', [Validators.required]],
    study: ['']
  });

  constructor(
    public sessionService: SessionService,
    public studyService: StudyService,
    public chosenCollaborationService: ChosenCollaborationService,
    private translateService: TranslateService,
    private fb: FormBuilder,
    private router: Router,
    private activatedRoute: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.activatedRoute.params.pipe(takeUntil(this.destroy$)).subscribe(async (params) => {
      const curSessionId = params['id'];
      if (curSessionId) {
        this.title = this.translateService.instant('session-create.edit-title');
        this.isLoading = true;
        this.session = await this.sessionService.getSession(curSessionId);
        this.form.controls['name'].setValue(this.session.name);
        this.form.controls['scope'].setValue(getEnumKeyByValue(SessionScope, this.session.scope));
        this.isLoading = false;
      } else {
        this.title = this.translateService.instant('session-create.create-title');
      }
    });
  }

  async handleSubmit(): Promise<void> {
    if (this.session && this.form.controls.name.value !== this.session.name) {
      const editTask = await this.sessionService.editSession(this.session.id.toString(), { name: this.form.controls.name.value });
      if (editTask) {
        this.router.navigate([routePaths.session, this.session.id]);
      }
      return;
    }

    if (this.form.valid) {
      const scope = SessionScope[this.form.controls.scope.value as keyof typeof SessionScope];
      const createSession: CreateSession = {
        name: this.form.controls.name.value,
        scope: scope,
        collaboration_id: this.collaboration?.id || -1
      };
      if (this.form.controls['study'].value && this.isScopeCollab()) {
        createSession.study_id = Number(this.form.controls['study'].value);
      }
      const newTask = await this.sessionService.createSession(createSession);
      if (newTask) {
        this.router.navigate([routePaths.sessions]);
      }
    }
  }

  public isScopeCollab(): boolean {
    return SessionScope[this.form.controls.scope.value as keyof typeof SessionScope] == SessionScope.Collaboration;
  }

  handleCancel(): void {
    this.session ? this.router.navigate([routePaths.session, this.session.id]) : this.router.navigate([routePaths.sessions]);
  }
}
