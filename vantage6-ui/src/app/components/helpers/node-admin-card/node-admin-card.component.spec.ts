import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NodeAdminCardComponent } from './node-admin-card.component';

describe('NodeAdminCardComponent', () => {
  let component: NodeAdminCardComponent;
  let fixture: ComponentFixture<NodeAdminCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [NodeAdminCardComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(NodeAdminCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
