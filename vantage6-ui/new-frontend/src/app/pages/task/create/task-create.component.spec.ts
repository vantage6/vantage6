import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskCreateComponent } from './task-create.component';

describe('TaskCreateComponent', () => {
  let component: TaskCreateComponent;
  let fixture: ComponentFixture<TaskCreateComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [TaskCreateComponent]
    });
    fixture = TestBed.createComponent(TaskCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
