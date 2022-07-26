import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NodeViewComponent } from './node-view.component';

describe('NodeViewComponent', () => {
  let component: NodeViewComponent;
  let fixture: ComponentFixture<NodeViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ NodeViewComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(NodeViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
