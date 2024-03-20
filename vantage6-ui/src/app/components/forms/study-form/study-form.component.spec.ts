import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StudyFormComponent } from './study-form.component';

describe('StudyFormComponent', () => {
  let component: StudyFormComponent;
  let fixture: ComponentFixture<StudyFormComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [StudyFormComponent]
    });
    fixture = TestBed.createComponent(StudyFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
