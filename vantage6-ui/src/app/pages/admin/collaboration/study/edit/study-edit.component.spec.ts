import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StudyEditComponent } from './study-edit.component';

describe('StudyEditComponent', () => {
  let component: StudyEditComponent;
  let fixture: ComponentFixture<StudyEditComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [StudyEditComponent]
    });
    fixture = TestBed.createComponent(StudyEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
