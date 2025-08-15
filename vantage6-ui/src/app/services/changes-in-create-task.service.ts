import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { BaseSession, Dataframe } from '../models/api/session.models';
import { BaseOrganization } from '../models/api/organization.model';

@Injectable({
  providedIn: 'root'
})
export class ChangesInCreateTaskService {
  private sessionChangeSubject = new BehaviorSubject<BaseSession | null>(null);
  public sessionChange$: Observable<BaseSession | null> = this.sessionChangeSubject.asObservable();

  private studyChangeSubject = new BehaviorSubject<number | null>(null);
  public studyChange$: Observable<number | null> = this.studyChangeSubject.asObservable();

  private dataframeChangeSubject = new BehaviorSubject<Dataframe[]>([]);
  public dataframeChange$: Observable<Dataframe[]> = this.dataframeChangeSubject.asObservable();

  private organizationChangeSubject = new BehaviorSubject<BaseOrganization[]>([]);
  public organizationChange$: Observable<BaseOrganization[]> = this.organizationChangeSubject.asObservable();

  constructor() {}

  emitSessionChange(session: BaseSession): void {
    this.sessionChangeSubject.next(session);
  }

  emitStudyChange(studyId: number | null): void {
    this.studyChangeSubject.next(studyId);
  }

  emitDataframeChange(dataframes: Dataframe[]): void {
    this.dataframeChangeSubject.next(dataframes);
  }

  emitOrganizationChange(organizations: BaseOrganization[]): void {
    this.organizationChangeSubject.next(organizations);
  }
}
