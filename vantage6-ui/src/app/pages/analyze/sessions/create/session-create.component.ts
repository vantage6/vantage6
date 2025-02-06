import { Component, HostBinding, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Subject } from 'rxjs';
import { Router } from '@angular/router';
import { routePaths } from 'src/app/routes';
import { CreateSession, SessionScope } from 'src/app/models/api/session.models';
import { SessionService } from 'src/app/services/session.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { BaseStudy } from 'src/app/models/api/study.model';
import { Collaboration } from 'src/app/models/api/collaboration.model';

@Component({
  selector: 'app-session-create',
  templateUrl: './session-create.component.html'
})
export class SessionCreateComponent implements OnInit {
  @HostBinding('class') class = 'card-container';

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
    public chosenCollaborationService: ChosenCollaborationService,
    private fb: FormBuilder,
    private router: Router
  ) {}

  ngOnInit(): void {}

  async handleSubmit(): Promise<void> {
    if (this.form.valid) {
      const scope = SessionScope[this.form.controls.scope.value as keyof typeof SessionScope];
      const createSession: CreateSession = {
        name: this.form.controls.name.value,
        scope: scope,
        collaboration_id: this.collaboration?.id || -1
      };
      if (this.form.controls['study'].value.length > 0 && this.isScopeCollab()) {
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
    this.goToPreviousPage();
  }

  private goToPreviousPage(): void {
    this.router.navigate([routePaths.sessions]);
  }
}
