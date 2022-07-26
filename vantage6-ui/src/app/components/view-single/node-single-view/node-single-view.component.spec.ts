import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NodeSingleViewComponent } from './node-single-view.component';

describe('NodeSingleViewComponent', () => {
  let component: NodeSingleViewComponent;
  let fixture: ComponentFixture<NodeSingleViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ NodeSingleViewComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(NodeSingleViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
