import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VisualizeTableComponent } from './visualize-table.component';

describe('Visualize-TableComponent', () => {
  let component: VisualizeTableComponent;
  let fixture: ComponentFixture<VisualizeTableComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [VisualizeTableComponent]
    });
    fixture = TestBed.createComponent(VisualizeTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
