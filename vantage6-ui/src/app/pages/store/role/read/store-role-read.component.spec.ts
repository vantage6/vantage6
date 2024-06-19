import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StoreRoleReadComponent } from './store-role-read.component';

describe('StoreRoleReadComponent', () => {
  let component: StoreRoleReadComponent;
  let fixture: ComponentFixture<StoreRoleReadComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [StoreRoleReadComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(StoreRoleReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
