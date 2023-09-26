import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CollaborationCreateComponent } from './collaboration-create.component';

describe('CollaborationCreateComponent', () => {
  let component: CollaborationCreateComponent;
  let fixture: ComponentFixture<CollaborationCreateComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [CollaborationCreateComponent]
    });
    fixture = TestBed.createComponent(CollaborationCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
