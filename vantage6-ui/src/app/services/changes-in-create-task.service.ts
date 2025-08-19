import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { BaseSession, Dataframe } from '../models/api/session.models';
import { BaseOrganization } from '../models/api/organization.model';
import { Algorithm, AlgorithmFunctionExtended } from '../models/api/algorithm.model';
import { Database } from '../models/api/node.model';

@Injectable({
  providedIn: 'root'
})
export class ChangesInCreateTaskService {
  private sessionChangeSubject = new BehaviorSubject<BaseSession | null>(null);
  public sessionChange$: Observable<BaseSession | null> = this.sessionChangeSubject.asObservable();

  private studyChangeSubject = new BehaviorSubject<number | null>(null);
  public studyChange$: Observable<number | null> = this.studyChangeSubject.asObservable();

  private functionChangeSubject = new BehaviorSubject<AlgorithmFunctionExtended | null>(null);
  public functionChange$: Observable<AlgorithmFunctionExtended | null> = this.functionChangeSubject.asObservable();

  private functionAlgorithmChangeSubject = new BehaviorSubject<Algorithm | null>(null);
  public functionAlgorithmChange$: Observable<Algorithm | null> = this.functionAlgorithmChangeSubject.asObservable();

  private dataframeChangeSubject = new BehaviorSubject<Dataframe[]>([]);
  public dataframeChange$: Observable<Dataframe[]> = this.dataframeChangeSubject.asObservable();

  private organizationChangeSubject = new BehaviorSubject<BaseOrganization[]>([]);
  public organizationChange$: Observable<BaseOrganization[]> = this.organizationChangeSubject.asObservable();

  private nodeDatabasesChangeSubject = new BehaviorSubject<Database[]>([]);
  public nodeDatabasesChange$: Observable<Database[]> = this.nodeDatabasesChangeSubject.asObservable();

  private selectedOrganizationIDsChangeSubject = new BehaviorSubject<string[]>([]);
  public selectedOrganizationIDsChange$: Observable<string[]> = this.selectedOrganizationIDsChangeSubject.asObservable();

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

  emitFunctionChange(function_: AlgorithmFunctionExtended | null): void {
    this.functionChangeSubject.next(function_);
  }

  emitfunctionAlgorithmChange(algorithm: Algorithm | null): void {
    this.functionAlgorithmChangeSubject.next(algorithm);
  }

  emitNodeDatabasesChange(databases: Database[]): void {
    this.nodeDatabasesChangeSubject.next(databases);
  }

  emitSelectedOrganizationIDsChange(organizationIDs: string[]): void {
    this.selectedOrganizationIDsChangeSubject.next(organizationIDs);
  }
}
