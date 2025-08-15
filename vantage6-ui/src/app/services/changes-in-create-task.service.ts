import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ChangesInCreateTaskService {
  // Study change observable
  private studyChangeSubject = new BehaviorSubject<number | null>(null);
  public studyChange$: Observable<number | null> = this.studyChangeSubject.asObservable();

  constructor() {}

  emitStudyChange(studyId: number | null): void {
    this.studyChangeSubject.next(studyId);
  }
}
