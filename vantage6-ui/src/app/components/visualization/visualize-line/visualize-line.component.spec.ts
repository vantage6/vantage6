import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VisualizeLineComponent } from './visualize-line.component';

describe('VisualizeLineComponent', () => {
  let component: VisualizeLineComponent;
  let fixture: ComponentFixture<VisualizeLineComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VisualizeLineComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(VisualizeLineComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
