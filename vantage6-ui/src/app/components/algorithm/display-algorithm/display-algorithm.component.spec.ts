import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DisplayAlgorithmComponent } from './display-algorithm.component';

describe('DisplayAlgorithmComponent', () => {
  let component: DisplayAlgorithmComponent;
  let fixture: ComponentFixture<DisplayAlgorithmComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DisplayAlgorithmComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(DisplayAlgorithmComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
