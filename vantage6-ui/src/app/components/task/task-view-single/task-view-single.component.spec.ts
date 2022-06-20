import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskViewSingleComponent } from './task-view-single.component';

describe('TaskViewSingleComponent', () => {
  let component: TaskViewSingleComponent;
  let fixture: ComponentFixture<TaskViewSingleComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TaskViewSingleComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TaskViewSingleComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
