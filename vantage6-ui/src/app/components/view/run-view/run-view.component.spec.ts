import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RunViewComponent } from './run-view.component';

describe('RunViewComponent', () => {
  let component: RunViewComponent;
  let fixture: ComponentFixture<RunViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [RunViewComponent],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(RunViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
