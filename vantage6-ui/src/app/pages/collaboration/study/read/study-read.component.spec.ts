import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StudyReadComponent } from './study-read.component';

describe('StudyReadComponent', () => {
  let component: StudyReadComponent;
  let fixture: ComponentFixture<StudyReadComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [StudyReadComponent]
    });
    fixture = TestBed.createComponent(StudyReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
