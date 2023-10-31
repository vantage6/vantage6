import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FilterStepComponent } from './filter-step.component';

describe('FilterStepComponent', () => {
  let component: FilterStepComponent;
  let fixture: ComponentFixture<FilterStepComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [FilterStepComponent]
    });
    fixture = TestBed.createComponent(FilterStepComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
