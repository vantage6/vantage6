import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NodeTableComponent } from './node-table.component';

describe('NodeTableComponent', () => {
  let component: NodeTableComponent;
  let fixture: ComponentFixture<NodeTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ NodeTableComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(NodeTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
