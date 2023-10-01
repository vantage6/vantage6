import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NodeReadComponent } from './node-read.component';

describe('NodeReadComponent', () => {
  let component: NodeReadComponent;
  let fixture: ComponentFixture<NodeReadComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [NodeReadComponent]
    });
    fixture = TestBed.createComponent(NodeReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
