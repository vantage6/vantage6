import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { BaseSession, Dataframe } from '../models/api/session.models';

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

  constructor() {}

  emitSessionChange(session: BaseSession | null): void {
    this.sessionChangeSubject.next(session);
  }

  emitStudyChange(studyId: number | null): void {
    this.studyChangeSubject.next(studyId);
  }

  emitDataframeChange(dataframes: Dataframe[]): void {
    this.dataframeChangeSubject.next(dataframes);
  }
}
