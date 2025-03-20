import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DisplayAlgorithmsComponent } from './display-algorithms.component';

describe('DisplayAlgorithmsComponent', () => {
  let component: DisplayAlgorithmsComponent;
  let fixture: ComponentFixture<DisplayAlgorithmsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DisplayAlgorithmsComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(DisplayAlgorithmsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
