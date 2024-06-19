import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StoreRoleCreateComponent } from './store-role-create.component';

describe('StoreRoleCreateComponent', () => {
  let component: StoreRoleCreateComponent;
  let fixture: ComponentFixture<StoreRoleCreateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [StoreRoleCreateComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(StoreRoleCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
