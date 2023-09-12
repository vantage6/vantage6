import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VisualizeResultComponent } from './visualize-result.component';

describe('VisualizeResultComponent', () => {
  let component: VisualizeResultComponent;
  let fixture: ComponentFixture<VisualizeResultComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [VisualizeResultComponent]
    });
    fixture = TestBed.createComponent(VisualizeResultComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
