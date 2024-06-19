import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StoreRoleEditComponent } from './store-role-edit.component';

describe('StoreRoleEditComponent', () => {
  let component: StoreRoleEditComponent;
  let fixture: ComponentFixture<StoreRoleEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [StoreRoleEditComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(StoreRoleEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
