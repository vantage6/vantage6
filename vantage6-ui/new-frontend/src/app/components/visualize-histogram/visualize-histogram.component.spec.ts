import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VisualizeHistogramComponent } from './visualize-histogram.component';

describe('VisualizeHistogramComponent', () => {
  let component: VisualizeHistogramComponent;
  let fixture: ComponentFixture<VisualizeHistogramComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [VisualizeHistogramComponent]
    });
    fixture = TestBed.createComponent(VisualizeHistogramComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
