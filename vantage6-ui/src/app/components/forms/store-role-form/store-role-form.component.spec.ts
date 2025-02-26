import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StoreRoleFormComponent } from './store-role-form.component';

describe('StoreRoleFormComponent', () => {
  let component: StoreRoleFormComponent;
  let fixture: ComponentFixture<StoreRoleFormComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [StoreRoleFormComponent]
    });
    fixture = TestBed.createComponent(StoreRoleFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
