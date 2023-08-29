import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskReadComponent } from './task-read.component';

describe('ReadComponent', () => {
  let component: TaskReadComponent;
  let fixture: ComponentFixture<TaskReadComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [TaskReadComponent]
    });
    fixture = TestBed.createComponent(TaskReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
