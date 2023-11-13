import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DatabaseStepComponent } from './database-step.component';

describe('DatabaseStepComponent', () => {
  let component: DatabaseStepComponent;
  let fixture: ComponentFixture<DatabaseStepComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [DatabaseStepComponent]
    });
    fixture = TestBed.createComponent(DatabaseStepComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
