import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CollaborationEditComponent } from './collaboration-edit.component';

describe('CollaborationEditComponent', () => {
  let component: CollaborationEditComponent;
  let fixture: ComponentFixture<CollaborationEditComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [CollaborationEditComponent]
    });
    fixture = TestBed.createComponent(CollaborationEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
